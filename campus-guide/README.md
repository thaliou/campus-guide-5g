# Guide du campus sur réseau 5G (hackathon)

Un nouvel arrivant scanne un QR code collé à un endroit précis du campus (entrée, parking, arrêt de bus). La page s'ouvre en sachant déjà où il se trouve, **sans GPS**. Il choisit sa destination parmi des boutons (aucune saisie au clavier) et voit le plus court chemin tracé sur le plan de l'école, avec la distance, le temps de marche, les repères à suivre et la photo du bâtiment d'arrivée.

Tout est servi **localement**, derrière l'UPF du cœur 5G OpenAirInterface : aucun accès Internet n'est nécessaire (pas de CDN, pas de Google Maps, pas de police web).

```
UE (10.0.x.x) --Uu--> gNB --N3 / GTP-U--> oai-upf (192.168.70.134) --N6--> campus-guide (192.168.70.140)
```

## Contenu

| Chemin | Rôle |
| --- | --- |
| `../docker-compose.campus.yml` | Ajoute le conteneur `campus-guide` (nginx) au réseau `oaiworkshop` |
| `app/index.html` | Application complète (HTML + CSS + JavaScript commenté) |
| `app/data/campus.json` | **Seul fichier à modifier pour changer de campus** : plan, départs, lieux, graphe des allées |
| `app/img/ept.svg` | Photo **provisoire** de l'école (page d'accueil), à remplacer par une vraie photo |
| `app/img/plan.svg` | Plan **schématique** à remplacer par le vrai plan de l'école |
| `app/img/*.svg` | Photos de remplacement, une par lieu |
| `app/img/photo-absente.svg` | Image affichée automatiquement si la photo d'un lieu manque |
| `app/qr/qr_<id>.png` | QR codes des points de départ |
| `app/vendor/` | Leaflet 1.9.4 embarqué (ne pas modifier) |
| `generer_qr.py` | Régénère les QR codes à partir de `campus.json` |

## Comment ça marche

- **Pages** : la partie après `#` de l'adresse choisit la page (`#/`, `#/depart`, `#/destination`, `#/trajet/<id>`, `#/lieux`, `#/apropos`). Le bouton « Retour » du téléphone fonctionne donc normalement. Un QR code (`?depart=entree`) mène directement au choix de la destination.

- **Carte** : Leaflet en mode `L.CRS.Simple`. Le plan est une simple image ; les coordonnées sont des **pixels de l'image**, origine en haut à gauche. Leaflet attend `[lat, lng]` avec l'axe vertical vers le haut, d'où la conversion `[hauteur - y, x]`.
- **Graphe** : les `noeuds` sont les portes de bâtiments, les carrefours et les points de départ ; les `aretes` relient deux nœuds par une allée réellement praticable. Le poids d'une arête est la distance euclidienne en pixels.
- **Itinéraire** : algorithme de **Dijkstra** exécuté dans le navigateur (fonction `plusCourtChemin` de `index.html`).
- **Distance** = pixels × `metresParPixel`. **Temps** = distance ÷ `vitesseMarcheKmh` (4,5 km/h), arrondi à la minute, 1 min minimum.
- **Étapes** : départ, puis chaque nœud traversé qui a un `nom` (« Passez par : Carrefour central »), puis l'arrivée.

### Format de `app/data/campus.json`

```json
{
  "ecole":  { "nom": "EPT", "titreAccueil": "Bienvenue à l'EPT", "sousTitre": "Trouvez votre chemin…", "photo": "img/ept.jpg" },
  "carte":  { "image": "img/plan.svg", "largeur": 1000, "hauteur": 700, "metresParPixel": 0.5, "vitesseMarcheKmh": 4.5 },
  "departs": [ { "id": "entree", "nom": "Entrée principale", "noeud": "entree" } ],
  "lieux":  [ { "id": "scolarite", "nom": "Scolarité", "categorie": "Démarches", "noeud": "d_scol",
                "photo": "img/scolarite.jpg", "description": "Inscriptions, certificats de scolarité." } ],
  "noeuds": { "entree": { "xy": [500, 650], "nom": "Entrée principale" }, "d_scol": { "xy": [400, 480] } },
  "aretes": [ ["entree", "d_scol"] ]
}
```

Le `nom` d'un nœud est facultatif : ne le mettez que sur les repères utiles (carrefours, places).

Le bloc `ecole` est facultatif : il règle la page d'accueil (nom affiché en haut à droite, titre, phrase d'accroche, grande photo).

## 1. Tester sur son PC (sans Docker)

`fetch()` est bloqué si on ouvre `index.html` en double-cliquant : il faut un petit serveur web.

```bash
cd campus-guide/app
python -m http.server 8000
```

Puis ouvrir dans le navigateur :

| Adresse | Résultat attendu |
| --- | --- |
| `http://localhost:8000/` | Page d'accueil (photo de l'école, bouton « S'orienter ») |
| `http://localhost:8000/?depart=entree` | Comme un scan du QR code : « Vous êtes à : Entrée principale » + lieux par catégorie |
| `http://localhost:8000/#/depart` | Écran « Où êtes-vous ? » avec un bouton par départ |
| `http://localhost:8000/#/lieux` | Tous les lieux avec leur photo et un bouton « Y aller » |
| `http://localhost:8000/#/apropos` | Présentation du projet et de l'équipe |
| `http://localhost:8000/?edit=1` | Mode édition (carte seule, relevé de coordonnées) |

Astuce : dans le navigateur, `F12` puis le mode « appareil mobile » (360 px de large) pour vérifier l'affichage sur téléphone. L'onglet **Réseau** ne doit montrer que des requêtes vers `localhost`.

## 2. Déployer sur le serveur de la formation

Placer `docker-compose.campus.yml` et le dossier `campus-guide/` à côté du `docker-compose.yaml` fourni (cœur 5G OAI), puis :

```bash
docker compose -f docker-compose.yaml -f docker-compose.campus.yml up -d
docker ps | grep campus-guide
curl -s http://192.168.70.140/ | head -5      # test depuis le serveur (hors 5G)
```

Le conteneur `campus-guide` (nginx:1.27-alpine) reçoit l'adresse `192.168.70.140` sur le réseau `public_net`. Au démarrage, il ajoute la route `10.0.0.0/16 via 192.168.70.134` : les réponses vers les UE repartent par l'UPF (d'où `cap_add: NET_ADMIN`). Le dossier `app/` est monté en lecture seule : modifier `campus.json` sur le serveur suffit, sans redémarrer.

L'image `nginx:1.27-alpine` doit être téléchargée une fois. **Sans Internet sur le serveur** : préparez-la à l'avance (`docker save nginx:1.27-alpine -o nginx.tar`, puis `docker load -i nginx.tar` sur le serveur), ou utilisez le plan B.

**Plan B sans nouvelle image** : servir l'application depuis `oai-ext-dn`, qui a déjà la bonne route, si `python3` y est présent :

```bash
docker exec oai-ext-dn which python3
docker cp campus-guide/app oai-ext-dn:/srv/app
docker exec -d oai-ext-dn python3 -m http.server 80 -d /srv/app
# l'adresse devient http://192.168.70.135/ : régénérer les QR codes (voir § 6)
```

## 3. Vérifier que le trafic passe bien par la 5G (depuis l'UE)

Avec la gNB et l'UE OAI en mode simulé (rfsim), l'UE crée une interface tunnel, en général `oaitun_ue1`, avec une adresse en `10.0.x.x` :

```bash
ip addr show oaitun_ue1
ping -I oaitun_ue1 -c 5 192.168.70.140
curl --interface oaitun_ue1 http://192.168.70.140/
curl --interface oaitun_ue1 http://192.168.70.140/data/campus.json | head
```

**Piège** : le serveur atteint aussi `192.168.70.140` directement par le bridge Docker, sans passer par la 5G. Pour qu'un navigateur passe par l'UE, forcez la route :

```bash
sudo ip route add 192.168.70.140/32 dev oaitun_ue1
```

Puis ouvrez `http://192.168.70.140/?depart=entree`. Preuve pour le jury : une capture sur le bridge montre les requêtes HTTP encapsulées dans GTP-U.

```bash
sudo tshark -i oaiworkshop -f "udp port 2152" -Y http
```

## 4. Faire passer un vrai téléphone par la 5G (optionnel)

Un téléphone ne peut pas s'attacher au réseau virtuel. En revanche, la machine où tourne l'UE peut jouer le rôle d'une **box 5G** : le téléphone s'y connecte en Wi-Fi et son trafic ressort par l'UE.

```bash
sudo sysctl -w net.ipv4.ip_forward=1
sudo iptables -t nat -A POSTROUTING -o oaitun_ue1 -j MASQUERADE
sudo ip route add 192.168.70.140/32 dev oaitun_ue1        # si pas déjà fait
nmcli dev wifi hotspot ifname <carte_wifi> ssid Campus5G password <motdepasse>
```

À présenter honnêtement : « l'UE joue le rôle d'un routeur 5G, comme les box 5G des opérateurs ».

## 5. Adapter au vrai campus

### 5.0 Remplacer la photo de l'école (page d'accueil)

Déposez la photo dans `app/img/` (par exemple `ept.jpg`, environ 1600 px de large, moins de 400 Ko), puis mettez `"photo": "img/ept.jpg"` dans le bloc `ecole` de `campus.json`. Une photo en format paysage, avec le bâtiment principal au centre, rend le mieux : le bas de l'image est assombri pour que le texte reste lisible.

### 5.1 Remplacer le plan

1. Copiez l'image du plan dans `app/img/` (par exemple `plan.png`). Une image d'environ 1500 à 2500 px de large convient bien.
2. Relevez sa taille en pixels (propriétés du fichier, ou un logiciel de dessin).
3. Dans `campus.json`, bloc `carte` : mettez `"image": "img/plan.png"`, `largeur` et `hauteur`.
4. **Échelle** : mesurez en pixels une longueur connue (par exemple un bâtiment de 60 m qui fait 240 px sur l'image) : `metresParPixel = 60 / 240 = 0.25`.

Si le plan change de taille, **toutes les coordonnées des nœuds doivent être relevées à nouveau**.

### 5.2 Tracer le graphe avec `?edit=1`

1. Ouvrez `http://localhost:8000/?edit=1` (ou `http://192.168.70.140/?edit=1`).
2. Les nœuds et allées déjà présents dans `campus.json` s'affichent en gris pointillé.
3. Cliquez sur chaque point de départ, carrefour et **porte** de bâtiment. Chaque clic place un point numéroté et ajoute une ligne dans la zone de texte :
   ```
   "n1": {"xy": [509, 191]},
   ```
4. Copiez ces lignes dans `"noeuds"`, puis renommez-les avec des noms parlants (`c_central`, `d_bib`…) et ajoutez un `"nom"` aux repères importants : `"c_central": {"xy": [500, 480], "nom": "Carrefour central"}`.
5. Dans `"aretes"`, reliez chaque paire de nœuds voisins par une allée **réellement marchable** : `["entree", "c_central"]`. Une allée qui tourne doit passer par un nœud à chaque virage, sinon le tracé coupe à travers les bâtiments.
6. Rechargez `?edit=1` : le message en haut indique **« ✔ Graphe connexe »** si tous les lieux sont atteignables depuis chaque départ, sinon la liste des trajets impossibles.

Attention au JSON : pas de virgule après le dernier élément d'une liste ou d'un objet. En cas d'erreur, la page affiche un message qui indique le problème.

### 5.3 Ajouter un lieu

1. Ajoutez sa porte dans `noeuds` et reliez-la au graphe dans `aretes`.
2. Ajoutez une entrée dans `lieux` :
   ```json
   { "id": "sport", "nom": "Terrain de sport", "categorie": "Vie étudiante", "noeud": "d_sport",
     "photo": "img/sport.jpg", "description": "Football, basket, athlétisme." }
   ```
3. Déposez la photo dans `app/img/` (JPEG d'environ 1000 px de large, moins de 300 Ko pour un chargement rapide). Si elle manque, `photo-absente.svg` est affichée à la place.

Les `categorie` deviennent les rubriques de l'écran de choix, dans l'ordre où elles apparaissent.

### 5.4 Ajouter un point de départ

Ajoutez une entrée dans `departs` (`id`, `nom`, `noeud`), puis régénérez les QR codes.

## 6. Générer les QR codes

```bash
pip install qrcode pillow
cd campus-guide
python generer_qr.py                          # adresse par défaut : http://192.168.70.140/
python generer_qr.py http://192.168.70.135/   # autre adresse (plan B)
```

Le script lit `app/data/campus.json` et crée `app/qr/qr_<id>.png` pour chaque départ ; chacun ouvre `<adresse>?depart=<id>`. Chaque QR code doit être collé **à l'endroit qu'il désigne** : c'est lui qui donne le point de départ.

## 7. Liste de contrôle avant la démo

- [ ] `/?depart=entree` : chaque lieu affiche un trajet.
- [ ] `/` sans paramètre : la page d'accueil apparaît ; « S'orienter » mène au choix du départ.
- [ ] Le bouton « Retour » du téléphone revient bien à la page précédente.
- [ ] `/?edit=1` : les clics affichent des coordonnées et le message « Graphe connexe ».
- [ ] Onglet Réseau (F12) : aucune requête vers une adresse externe.
- [ ] Console (F12) : aucune erreur.
- [ ] `curl --interface oaitun_ue1 http://192.168.70.140/` répond.

## Idées d'extension

- Statistiques anonymes des destinations demandées (petite API + Prometheus + Grafana).
- Version bilingue français / wolof / anglais.
- Lecture vocale des étapes pour les personnes malvoyantes.
