# Labo 04 – Optimisation, Caching, Load Balancing, Test de charge, Observabilité

<img src="https://upload.wikimedia.org/wikipedia/commons/2/2a/Ets_quebec_logo.png" width="250">    
ÉTS - LOG430 - Architecture logicielle - Chargé de laboratoire: Gabriel C. Ullmann.

## 🎯 Objectifs d'apprentissage
- Apprendre à configurer [Prometheus](https://prometheus.io/docs/introduction/overview/)
- Apprendre à effectuer des tests de charge avec [Locust](https://docs.locust.io/en/stable/what-is-locust.html)
- Comprendre les types d'optimisation possibles dans le contexte du Store Manager ainsi que les avantages et inconvénients de chacun
- Apprendre à implémenter le cache en mémoire avec Redis et l'équilibrage de charge (load balancing) avec [Nginx](https://nginx.org/en/docs/http/load_balancing.html)

## ⚙️ Setup

Dans ce laboratoire, on continuera à utiliser la même version du Store Manager développée au laboratoire 03, mais nous ferons quelques petites modifications. Le but n'est pas d'ajouter de nouvelles fonctionnalités, mais de mesurer et comparer la performance de lecture/écriture de l'application en utilisant MySQL et Redis. Après avoir mesuré et comparé, nous allons implémenter deux approches d'optimisation : caching et load balancing.

En résumé, dans ce laboratoire, nous nous concentrerons non seulement sur la surveillance (mesure des variables et observation passive), mais aussi sur l'observabilité (agir sur nos observations pour modifier le logiciel ou son environnement).

> ⚠️ **IMPORTANT** : Les documents ARC42 et ADR contenus dans ce dépôt sont identiques à ceux du laboratoire 03, car nous ne modifions pas l'architecture de l'application dans ce laboratoire.

> 📝 **NOTE** : À partir de ce laboratoire, nous vous encourageons à utiliser la bibliothèque `logger` plutôt que la commande `print`. Bien que `print` fonctionne bien pour le débogage, l'utilisation d'un logger est une bonne pratique de développement logiciel car il offre [plusieurs avantages lorsque notre application entre en production](https://www.geeksforgeeks.org/python/difference-between-logging-and-print-in-python/). Vous trouverez un exemple d'utilisation du `logger` et plus de détails dans `src/stocks/commands/write_stock.py`.

### 1. Créez un nouveau dépôt à partir du gabarit et clonez le dépôt
```bash
git clone https://github.com/[votredepot]/log430-labo4
cd log430-labo4
```

### 2. Créez un réseau Docker
Exécutez dans votre terminal :
```bash
docker network create labo04-network
```

### 3. Générez des données fictives (mock data)
Pendant ce labo, nous réaliserons des tests de charge. Ça veut dire qu'on mettra beaucoup de pression sur l'application pour observer ses limitations de performance. Pour créer un environnement de test similaire à un environnement de production dans un vrai magasin, il faut utiliser une grande quantité de données. Pour faire ça, nous utiliserons le script `generators/data_generator.py`. Exécutez ce script dans votre ordinateur **avant** de démarrer le conteneur Docker. Le script créera des commandes INSERT (MySQL) et SET (Redis) pour :
- 500 utilisateurs (alloués aux commandes de façon aléatoire)
- 10 000 articles (avec des quantités de stock aléatoires)
- 80 000 commandes (avec 1-5 articles par commande, choisis de façon aléatoire)

> 📝 **NOTE** : Ces chiffres correspondent à ce que 2 magasins pourraient accumuler dans 1 an d'utilisation continue du Store Manager s'ils enregistrent environ 110 commandes par jour, ou 3 magasins pendant 1 an avec 75 commandes par jour.

Les commandes MySQL et Redis générées par le script seront exécutées de façon automatique pendant le démarrage des conteneurs Docker. Vous n'avez aucune action à effectuer, mais vous devrez peut-être patienter quelques secondes jusqu'à ce que la création soit terminée. Vous pouvez vérifier l'état de votre serveur MySQL ou Redis en consultant les logs Docker.

### 4. Préparez l'environnement de développement
Suivez les mêmes étapes que dans le laboratoire dernier.

### 5. Installez Postman
Suivez les mêmes étapes que dans le laboratoire dernier. Importez la collection disponible dans `/docs/collections`.

## 🧪 Activités pratiques
Pendant le labo 02, nous avons implémenté le cache avec Redis. Pendant le labo 03, nous avons utilisé ce cache pour les endpoints des rapports. Dans ce labo, nous allons temporairement désactiver Redis pour mesurer la différence entre les lectures directement de MySQL vs Redis. Pour faciliter les comparaisons, dans ce laboratoire les méthodes qui font la génération de rapport dans `queries/read_order.py` ont 2 versions : une pour MySQL, une autre pour Redis.

### 1. Désactivez le cache Redis temporairement
Dans `queries/read_order.py`, remplacez l'appel à `get_highest_spending_users_redis` par `get_highest_spending_users_mysql`. Également, remplacez l'appel à `get_best_selling_products_redis` par `get_best_selling_products_mysql`. Ça sera important pour notre test de charge à partir de l'activité 5.

### 2. Instrumentez Flask avec Prometheus
Dans `store_manager.py`, ajoutez un endpoint `/metrics`, qui permettra à Prometheus de lire l'état des variables que nous voulons observer dans l'application.
```python
@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}
```

N'oubliez pas d'ajouter également les `imports` suivants :
```python
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
```

### 3. Créez des Counters 
Également dans `store_manager.py`, ajoutez les objets [Counter](https://prometheus.io/docs/concepts/metric_types/#counter) pour compter le nombre de requêtes aux endpoints `/orders`, `/orders/reports/highest-spenders` et `/orders/reports/best-sellers`. N'oubliez pas d'appeler la méthode `inc()` pour incrémenter la valeur du compteur à chaque requête. Par exemple :

```python
counter_orders = Counter('orders', 'Total calls to /orders')
@app.post('/orders')
def post_orders():
    counter_orders.inc()
```

Reconstruisez puis redémarrez le conteneur Docker.
```bash
docker compose down -v && docker compose up -d --build                     
```

> 💡 **Question 1** : Veuillez consulter le endpoint `/metrics` et observer les variables produites. Copiez et collez ici un exemple des métriques `orders`, `orders_reports_highest_spenders` et `orders_reports_best_sellers`.

### 4. Installez et configurez Prometheus
Téléchargez la dernière version de Prometheus pour votre système d'exploitation à partir de la [page des versions](https://prometheus.io/download/).

> 💡 **Question 2** : Quelle est la version la plus récente de Prometheus que vous avez téléchargée ?

Extrayez l'archive téléchargée et naviguez dans le répertoire extrait. Ensuite, ouvrez le fichier `prometheus.yml` et ajoutez ce qui suit à la fin :
```yaml
scrape_configs:
  - job_name: 'flask_app'
    static_configs:
      - targets: ['localhost:5000']
```

Lancez Prometheus en exécutant le binaire Prometheus. Par exemple, sous Linux et macOS :
```bash
./prometheus --config.file=prometheus.yml
```

Ouvrez http://localhost:9090/targets dans votre navigateur web. Vous devriez voir une liste indiquant l'état de votre instance `flask_app`. Si elle est marquée comme UP, vous avez configuré Prometheus avec succès. Si elle est DOWN ou absente, vérifiez que le port Flask est accessible et que la cible est correctement configurée.

> 💡 **Question 3** : Veuillez ajouter une capture d'écran de http://localhost:9090/targets montrant que l'état de l'instance `flask_app` est UP.

### 5. Testez la charge sans optimisation
Installez et exécutez Locust en suivant [ces instructions](https://docs.locust.io/en/stable/installation.html). Locust est un outil de test de charge qui vous permet de simuler plusieurs utilisateurs interagissant avec votre application. Par défaut, dans Locust, chaque utilisateur simulé (`User`) exécute ses tâches en boucle et dans un ordre aléatoire.

Le fichier de test Locust se trouve dans `locust/locust_test.py`. Il crée des utilisateurs qui effectuent des requêtes sur les endpoints `/orders` (POST), `/orders/reports/highest-spenders` (GET) et `/orders/reports/best-sellers` (GET). L'objectif de ce test est de découvrir les goulots d'étranglement, puis de mesurer les améliorations apportées par les optimisations suivantes : cache et load balancing.

Exécutez Locust avec la commande suivante. Il vous sera demandé de choisir un nombre d'utilisateurs simultanés (par exemple, 100 utilisateurs), un taux d'éclosion (nombre de nouveaux utilisateurs à créer par seconde, par exemple, 10) et une durée de test (300 secondes).
```bash
locust -f locust/locust_test.py
```

Ce qui se passe en arrière-plan : Locust commencera à générer un nombre croissant d'utilisateurs jusqu'à ce qu'il atteigne le nombre total que vous avez spécifié. De façon continue, chaque utilisateur créé exécutera les tâches définies dans `locust_test.py` en boucle. 

Observez l'onglet `Statistics` et regardez les métriques suivantes : requêtes totales, nombre d'échecs, temps de réponse médian, temps de réponse du 95e percentile et requêtes par seconde. Notez les valeurs pour chacun de vos endpoints. Vous pouvez également observer l'onglet `Charts` pour voir les graphiques de la charge et de la latence.

### 6. Optimisez l'implémentation du endpoint `/orders`
Lorsque nous créons une commande dans `commands/write_order.py`, dans la méthode `add_order`, nous collectons les prix de tous les produits de la commande. Pour le moment, nous effectuons une requête à la base de données pour chaque produit (dans une boucle), ce qui peut être très lent lorsque nous ajoutons une commande qui comporte plusieurs produits.

```python
# ❌ Code non-optimisé
product_prices = {}
for product_id in product_ids:
    product = session.query(Product).filter(Product.id == product_id).all()
    product_prices[product_id] = product[0].price
```

Pour résoudre ce problème, modifiez la méthode `add_order` de façon à collecter et récupérer tous les `product_ids` en une seule requête. Nous utiliserons toujours une boucle `for`, mais la requête de base de données **ne se trouvera pas dans la boucle**.
```python
# ✅ Code optimisé
product_prices = {}
product_ids = [1, 2, 3] # TODO: Collectez le product_id de chaque OrderItem dans la commande
products = session.query(Product).filter(Product.id.in_(product_ids)).all()
for product in products:
    product_prices[product.id] = product.price
```

Redémarrez votre conteneur `store_manager` pour vous assurer qu'aucun processus issu du test de charge précédent n'est en cours d'exécution. 
```bash
docker compose restart store_manager                  
```

Ensuite, **relancez les tests Locust** avec les mêmes paramètres de la dernière activité. Observez et répondez aux questions.

> 💡 **Question 4** : Sur l'onglet `Statistics`, comparez les résultats actuels avec les résultats du test de charge précédent. Est-ce que vous voyez quelques différences significatives dans les métriques pour l'endpoint `POST /orders` ?

> 💡 **Question 5** : Si nous avions plus d'articles dans notre base de données (par exemple, 1 million), ou simplement plus d'articles par commande en moyenne, le temps de réponse de l'endpoint `POST /orders` augmenterait-il, diminuerait-il ou resterait-il identique ?

Enregistrez le contenu du tableau `Statistics`, nous l'utiliserons plus tard pour comparer les tests suivants (par exemple, vous pouvez copier-coller le tableau dans Excel/Google Sheets ou dans un fichier texte).

> 📝 **NOTE** : Bien que cela ne s'applique pas à ce laboratoire, dans des applications plus complexes, de nombreuses mesures peuvent être implémentées pour améliorer la performance de lecture de la base de données, telles que la [création d'index](https://www.w3schools.com/mysql/mysql_create_index.asp) et la [normalisation](https://www.ibm.com/fr-fr/think/topics/database-normalization). Nous pouvons également augmenter le [nombre de connexions disponibles dans MySQL](https://dev.mysql.com/doc/refman/8.4/en/server-system-variables.html#sysvar_max_connections) pour prendre en charge plus d'utilisateurs. Bien que valables, ces solutions ne sont toutefois que des palliatifs si le problème fondamental réside dans un nombre important de requêtes simultanées. Ce sujet est abordé en plus de détail dans la dernière section de ce document.

### 7. Réactivez Redis et optimisez la génération des rapports

Dans `queries/read_order.py`, remplacez l'appel à `get_highest_spending_users_mysql` par `get_highest_spending_users_redis`. Également, remplacez l'appel à `get_best_selling_products_mysql` par `get_best_selling_products_redis`.

Redémarrez votre conteneur `store_manager` pour vous assurer qu'aucun processus issu du test de charge précédent n'est en cours d'exécution. Ensuite, **relancez les tests Locust** avec les mêmes paramètres de la dernière activité. Observez et enregistrez le contenu du tableau `Statistics`, nous l'utiliserons plus tard pour comparer les tests suivants (par exemple, vous pouvez copier-coller le tableau dans Excel/Google Sheets ou dans un fichier texte).

Contrairement à ce que l'on pourrait croire, vous constaterez une augmentation générale du temps de réponse et une diminution du nombre de requêtes traitées. Mais pourquoi ? Même si Redis est en mémoire et que l'accès à la mémoire est rapide, nous l'interrogeons très fréquemment pour obtenir la liste de commandes (`r.keys("order:*")`), puis nous parcourons cette liste, récupérons l'objet commande (`r.hgetall(key)`) et le traitons pour générer le rapport. Cette approche prend trop de temps, et la durée nécessaire augmente proportionnellement avec la quantité de commandes et d'articles par commande. Pour résoudre ce problème, nous devons conserver le rapport en cache pendant une période déterminée. Le rapport ne sera désormais plus mis à jour en temps réel, mais cette solution nous permettra de servir des rapports très récents de manière quasi instantanée.

Veuillez copier et coller le code optimisé fourni dans le répertoire `/optimization`. Vous devez mettre à jour l'implémentation de `src/orders/queries/read_order.py` et ajoutez l'extrait de code fourni au fichier `src/store_manager.py` après la déclaration de la variable `app`. n'oubliez pas de mettre à jour les appels aux rapports dans `src/orders/controllers/order_controller.py` en ajoutant le paramètre `skip_cache` dans le 2 fonctions :

```py
def get_report_highest_spending_users(skip_cache=False):
    """Get orders report: highest spending users"""
    return get_highest_spending_users(skip_cache)

def get_report_best_selling_products(skip_cache=False):
    """Get orders report: best selling products"""
    return get_best_selling_products(skip_cache)
```

Le code optimisé fera ce qui suit :
1. Générer les 2 rapports et les enregistrer dans Redis dès que le Store Manager démarre. Dans ce cas, il ignorera simplement tout cache existant (`skip_cache=True`).
2. Les méthodes de génération de rapports ne liront que le rapport entièrement rendu déjà mis en cache dans Redis (`skip_cache=False`), sans essayer de le régénérer à chaque fois ni de le régénérer depuis MySQL.
3. Les rapports seront régénérés toutes les 60 secondes afin d'afficher les dernières modifications. Peu importe le temps que prendra la génération, l'ancien rapport sera livré aux utilisateurs jusqu'à ce que le nouveau soit disponible. Ainsi, le cache ne sera jamais vide et cela permet d'éviter un problème de [cache stampede](https://www.geeksforgeeks.org/system-design/cache-stempede-or-dogpile-problem-in-system-design/).

> 📝 **NOTE** : Techniquement, régénérer les rapports toutes les 60 secondes est un gaspillage de ressources, car nous les régénérerons même si personne ne les utilise ou même lorsqu'il n'y a pas de changement. Cependant, il s'agit d'une optimisation simplifiée à des fins didactiques pour ce laboratoire. Si vous souhaitez en savoir plus sur les solutions robustes et élégantes aux problèmes de « cache stampede » et « thundering herds », veuillez lire cet article : [Thundering Herds: The Scalability Killer](https://docs.aonnis.com/blog/thundering-herds-the-scalability-killer).

Redémarrez vos conteneurs `store_manager` et `redis` pour vous assurer qu'aucun processus issu du test de charge précédent n'est en cours d'exécution. Ensuite, **relancez les tests Locust** avec les mêmes paramètres de la dernière activité.

> 💡 **Question 6** : Sur l'onglet `Statistics`, comparez les résultats actuels avec les résultats du test de charge précédent. Est-ce que vous voyez quelques différences significatives dans les métriques pour les endpoints `POST /orders`, `GET /orders/reports/highest-spenders` et `GET /orders/reports/best-sellers` ? Dans quelle mesure la performance s'est-elle améliorée ou détériorée (par exemple, en pourcentage) ?

> 💡 **Question 7** : La génération de rapports repose désormais entièrement sur des requêtes adressées à Redis, ce qui réduit la charge pesant sur MySQL. Cependant, le point de terminaison `POST /orders` reste à la traîne par rapport aux autres en termes de performances dans notre scénario de test. Alors, qu'est-ce qui limite les performances de l'endpoint `POST /orders` ?

Encore une fois, enregistrez le contenu du tableau `Statistics`, nous l'utiliserons plus tard pour comparer les tests suivants.

### 8. Testez l'équilibrage de charge (load balancing) avec Nginx
Pour tester le scénario suivant, utilisez le répertoire `load-balancer-config` :
- Copiez le texte dans `docker-compose-to-copy-paste.txt` et collez-le dans `docker-compose.yml`
- Créez un fichier `nginx.conf` dans le répertoire racine du projet.
- Copiez le texte dans `nginx-conf-to-copy-paste.txt` et collez-le dans le fichier `nginx.conf`
Observez les modifications apportées à `docker-compose.yml`. 

Finalement, redémarrez vos conteneurs `store_manager` et `redis` pour vous assurer qu'aucun processus issu du test de charge précédent n'est en cours d'exécution. Ensuite, **relancez les tests Locust** avec les mêmes paramètres de la dernière activité. Enregistrez le contenu du tableau `Statistics`, nous l'utiliserons plus tard pour comparer les tests suivants.

> 💡 **Question 8** : Sur l'onglet `Statistics`, comparez les résultats actuels avec les résultats du test de charge précédent. Est-ce que vous voyez quelques différences significatives dans les métriques pour les endpoints `POST /orders`, `GET /orders/reports/highest-spenders` et `GET /orders/reports/best-sellers` ? Dans quelle mesure la performance s'est-elle améliorée ou détériorée (par exemple, en pourcentage) ? Pour cette question, la réponse dépendra de votre environnement d'exécution (par exemple, vous obtiendrez de meilleures performances en exécutant deux instances du Store Manager sur deux serveurs physiques distincts).

> 💡 **Question 9** : Dans le fichier `nginx.conf`, il existe un attribut qui configure l'équilibrage de charge. Quelle politique d'équilibrage de charge utilisons-nous actuellement ? Consultez la documentation officielle Nginx si vous avez des questions.

### ⭐ Points clés à retenir de ce labo
L'objectif de ce laboratoire n'est pas de résoudre tous les problèmes de performance de l'application Store Manager, mais de la pousser à ses limites afin que nous puissions observer comment elle réagit et l'optimiser en conséquence. Voici quelques points importants :

1. **La mesure est fondamentale**. Même lorsque votre intuition vous dit que votre nouvelle implémentation devrait apporter une amélioration (par exemple, le cache avec Redis), cela peut ne pas être le cas, car elle entraîne une conséquence imprévue (surcharge des serveurs Python et Redis). Cela peut être difficile à déterminer si vous ne mesurez pas les performances et n'observez pas les chiffres.
2. **Les métriques servent à la prise de décision**. Il est important non seulement de mesurer et observer, mais aussi d'agir en fonction de nos mesures, et d'être en mesure de dire dans quelle mesure une implémentation est meilleure ou pire par rapport à une autre.
3. **Les effets d'une optimisation ne sont pas isolés**. Lorsque nous modifions l'implémentation ou l'architecture de notre application pour améliorer une métrique, nous pouvons en détériorer une autre.
4. Dans une application monolithique et synchrone telle que Store Manager, la **base de données devient rapidement une limitation**, en particulier si notre exigence est de prendre en charge un grand nombre d'utilisateurs simultanés. La solution consiste à procéder à une mise à l'échelle verticale (par exemple, ajouter plus de RAM/CPU à votre serveur), puis à une mise à l'échelle horizontale (équilibrage de charge), et enfin migrer vers une autre architecture (par exemple, les microservices event-driven). Nous aborderons certains de ces sujets dans les prochains laboratoires.

## 📦 Livrables

- Un fichier .zip contenant l'intégralité du code source du projet Labo 04.
- Un rapport en .pdf répondant aux questions présentées dans ce document. Il est obligatoire d'illustrer vos réponses avec du code ou des captures d'écran/terminal.