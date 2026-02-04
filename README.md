# Labo 04 – Optimization, Caching, Load Balancing, Test de charge, Observabilité

<img src="https://upload.wikimedia.org/wikipedia/commons/2/2a/Ets_quebec_logo.png" width="250">    
ÉTS - LOG430 - Architecture logicielle - Chargé de laboratoire: Gabriel C. Ullmann.

## 🎯 Objectifs d'apprentissage
- Apprendre à configurer Prometheus
- Apprendre à effectuer les tests de charge avec [Locust](https://docs.locust.io/en/stable/what-is-locust.html)
- Comprendre les types d'optimisation possibles ainsi que les avantages et inconvénients de chacun
- Apprendre à implémenter le cache en mémoire avec Redis et l'équilibrage de charge (load balancing) avec [Nginx](https://nginx.org/en/docs/http/load_balancing.html)

## ⚙️ Setup

Dans ce laboratoire, on continuera à utiliser la même version du « store manager » développée au laboratoire 03, mais nous ferons quelques modifications. Le but n'est pas d'ajouter de nouvelles fonctionnalités, mais de mesurer et comparer la performance de lecture/écriture de l'application en utilisant MySQL et Redis. Après avoir mesuré et comparé, nous allons implémenter deux approches d'optimisation : caching et load balancing.

En résumé, dans ce laboratoire, nous nous concentrerons non seulement sur la surveillance (mesure des variables et observation passive), mais aussi sur l'observabilité (agir sur nos observations pour modifier le logiciel ou son environnement).

> ⚠️ **IMPORTANT** : Les documents ARC42 et ADR contenus dans ce dépôt sont identiques à ceux du laboratoire 03, car nous ne modifions pas l'architecture de l'application dans ce laboratoire.

> 📝 NOTE : À partir de ce laboratoire, nous vous encourageons à utiliser la bibliothèque `logger` plutôt que la commande `print`. Bien que `print` fonctionne bien pour le débogage, l'utilisation d'un logger est une bonne pratique de développement logiciel car il offre [plusieurs avantages lorsque notre application entre en production](https://www.geeksforgeeks.org/python/difference-between-logging-and-print-in-python/). Vous trouverez un exemple d'utilisation du `logger` et plus de détails dans `src/stocks/commands/write_stock.py`.

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

### 3. Préparez l'environnement de développement
Suivez les mêmes étapes que dans le laboratoire dérnier.

### 4. Installez Postman
Suivez les mêmes étapes que dans le laboratoire dérnier. Importez la collection disponible dans `/docs/collections`.

## 🧪 Activités pratiques
Pendant le labo 02, nous avons implémenté le cache avec Redis. Pendant le labo 03, nous avons utilisé ce cache pour les endpoints des rapports. Dans ce labo, nous allons temporairement désactiver le Redis pour mesurer la différence entre les lectures directement de MySQL vs Redis. Pour faciliter les comparaisons, dans ce laboratoire les méthodes qui font la génération de rapport dans `queries/read_order.py` ont 2 versions : une pour MySQL, autre pour Redis.

### 1. Désactivez le cache Redis temporairement
Dans `queries/read_order.py`, remplacez l'appel à `get_highest_spending_users_redis` par `get_highest_spending_users_mysql`. Également, remplacez l'appel à `get_best_selling_products_redis` par `get_best_selling_products_mysql`.

### 2. Instrumentez Flask avec Prometheus
Dans `store_manager.py`, ajoutez un endpoint `/metrics`, qui permettra à Prometheus de lire l'état des variables que nous voulons observer dans l'application.
```python
@app.route("/metrics")
def metrics():
    return generate_latest(), 200, {"Content-Type": CONTENT_TYPE_LATEST}
```

N'oubliez pas d'ajouter également les `imports` suivants:
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

Reconstruisez et puis redémarrez le conteneur Docker.
```bash
docker compose down -v && docker compose up -d --build                     
```

### 4. Observez les métriques dans Prometheus
Dans Postman, faites quelques requêtes à `POST /orders`. Ensuite, accédez à Prometheus sur `http://localhost:9090` et exécutez une requête (query) à `orders_total`. Vous devriez voir une valeur numérique associée à la variable. Faites la même chose pour les deux autres `Counters`. Par exemple, si vous avez nommé le compteur `highest_spenders`, exécutez une requête à `highest_spenders_total`. Cliquez sur `Graph` pour voir la représentation visuelle de chaque variable. Faites quelques requêtes de plus pour voir le changement des variables.

> 📝 **NOTE** : Prometheus ne met pas automatiquement à jour les variables dans l'interface Web lorsqu'elles changent dans le serveur. Vous devez cliquer sur `Query` ou recharger la page Web pour voir les valeurs mises à jour.

### 5. Lancez un test de charge avec Locust
Le script `locustfiles/locustfile.py` lorsqu'il est exécuté, effectuera plusieurs appels vers des endpoints (représentés par les méthodes `@task`), simulant ainsi des utilisateurs réels. Dans un premier temps, nous ne modifierons pas ce script, nous l'activerons simplement à partir de l'interface web à Locust.

Accédez à `http://localhost:8089` et appliquez les paramètres suivantes :
- **Host** : De préférence, exécutez le test de charge sur un serveur externe (par exemple, une VM LXD). Ouvrez le port 5000 et d'autres ports si nécessaire. Si vous n'avez pas accès à une VM, vous pouvez installer [votre propre instance LXD](https://canonical.com/lxd/install) sur une VM Linux dans votre ordinateur à l'aide d'Oracle VirtualBox ou d'un autre logiciel similaire. Alternativement, si cette option ne fonctionne pas non plus pour vous, vous pouvez exécuter le test de charge directement dans votre ordinateur, sans utiliser une VM.
- **Number of users (nombre d'utilisateurs)** : 100
- **Spawn rate (taux d'apparition des nouveaux utilisateurs)** : 1 (par seconde)

Lancez le test et observez les statistiques et graphiques dans Locust (onglet `Charts`). En un peu moins de 2 minutes, vous devriez observer que votre application reçoit une charge de requêtes équivalente à 100 utilisateurs simultanés.

> 📝 **NOTE** : Les indicateurs mesurés par Locust correspondent aux [4 métriques d'or](https://sre.google/sre-book/monitoring-distributed-systems/#xref_monitoring_golden-signals) définis par Google.

> 💡 **Question 1** : Quelle est la latence moyenne (50ème percentile) et le taux d'erreur observés avec 100 utilisateurs ? Illustrez votre réponse à l'aide des graphiques Locust (onglet `Charts`).

### 6. Écrivez un nouveau test de charge avec Locust
Dans le répertoire `locustfiles/experiments/locustfile_read_write.py`, complétez le script `locustfile_read_write.py` pour ajouter une commande en utilisant des valeurs aléatoires et une proportion d'exécution des méthodes `@task` à 66% lectures, 33% écritures (proportion d'exécution des fonctions : 1:1:1). Plus d'informations sur la proportion d'exécution des appels de chaque méthode `@task` [dans la documentation officielle à Locust](https://docs.locust.io/en/stable/writing-a-locustfile.html#task-decorator).

Finalement, copiez le code modifié de `locustfiles/experiments/locustfile_read_write.py` à `locustfiles/locustfile.py`. Reconstruisez et puis redémarrez le conteneur Docker.
```bash
docker compose down -v && docker compose up -d --build                     
```
Relancez les tests Locust avec les mêmes paramètres de la dernière activité. Si cela fonctionne, passez à l'activité 7.

### 7. Augmentez la charge
Augmentez progressivement le nombre d'utilisateurs jusqu'à ce que l'application échoue (par exemple, jusqu'à obtenir une quantité importante d'erreurs 500, de timeouts, etc.). Regardez l'onglet `Failures` pour plus d'informations sur les erreurs.

> 💡 **Question 2** : À partir de combien d'utilisateurs votre application cesse-t-elle de répondre correctement (avec MySQL) ? Illustrez votre réponse à l'aide des graphiques Locust.

### 8. Optimisez la lecture des données des articles
Avant d'envisager un changement de base de données, de serveur Web ou une augmentation des ressources matérielles (RAM/CPU) sur notre serveur on-premises ou en nuage, il est raisonnable de vérifier si une optimisation du code existant est possible. Cette approche présente généralement le meilleur rapport coût-efficacité.

Dans `orders/commands/write_order.py`, si nous regardons attentivement la fonction `add_order`, nous verrons qu'elle ne récupère pas les informations des articles de manière efficace. Si nous avions, par exemple, 100 articles dans notre commande, la fonction effectuerait 100 requêtes à la base de données pour chercher les informations sur les articles ([problème N+1](https://planetscale.com/blog/what-is-n-1-query-problem-and-how-to-solve-it)). À fur et a mesure que le nombre d'articles augmente dans la base, le temps de recherche augmente également.

```python
# ❌ Code non-optimisé
product_prices = {}
for product_id in product_ids:
    product = session.query(Product).filter(Product.id == product_id).all()
    product_prices[product_id] = product[0].price
```

Modifiez la méthode `add_order` de façon à collecter et récupérer tous les `product_ids` en une seule requête. Nous utiliserons toujours une boucle `for`, mais la requête de base de données **ne se trouve pas dans la boucle**.
```python
# ✅ Code optimisé
product_prices = {}
product_ids = [1, 2, 3] # Collectez le product_id de chaque OrderItem
products = session.query(Product).filter(Product.id.in_(product_ids)).all()
for product in products:
    product_prices[product.id] = product.price
```

> 📝 NOTE : Ceci n'est qu'un exemple trivial d'optimisation de lecture. Dans une application réelle, il faut parfois effectuer des ajustements plus granulaires dans la base de données, comme la [création d'index](https://www.w3schools.com/mysql/mysql_create_index.asp) et la [normalisation](https://www.ibm.com/fr-fr/think/topics/database-normalization). Nous pouvons également augmenter le [nombre de connexions disponibles dans MySQL](https://dev.mysql.com/doc/refman/8.4/en/server-system-variables.html#sysvar_max_connections). Il ne s'agit pas vraiment d'une optimisation, mais plutôt d'une solution provisoire.

Reconstruisez et puis redémarrez le conteneur Docker.
```bash
docker compose down -v && docker compose up -d --build                     
```

Relancez les tests Locust avec les mêmes paramètres de la dernière activité.

> 💡 **Question 3** : À partir de combien d'utilisateurs votre application cesse-t-elle de répondre correctement (avec MySQL + optimisation) ? Illustrez votre réponse à l'aide des graphiques Locust.

### 9. Réactivez Redis
Dans `queries/read_order.py`, remplacez l'appel à `get_highest_spending_users_mysql` par `get_highest_spending_users_redis`. Également, remplacez l'appel à `get_best_selling_products_mysql` par `get_best_selling_products_redis`.

Cependant, avant de relancer les tests, nous devons optimiser la génération des rapports. Même si Redis est en mémoire et que l'accès est rapide, nous l'interrogeons très fréquemment pour obtenir la liste de commandes (`r.keys("order:*")`), puis nous parcourons cette liste, récupérons l'objet commande (`r.hgetall(key)`) et le traitons pour générer le rapport. Cette approche prend trop de temps, et la durée nécessaire augmente proportionnellement avec la quantité de commandes et d'articles par commande. Pour résoudre ce problème, nous devons conserver le rapport en cache pendant une période déterminée. Le rapport ne sera désormais plus mis à jour en temps réel, mais cette solution nous permettra de servir des rapports très récents de manière quasi instantanée.

Dans `orders/queries/read_order.py`, à la fin de la méthode `get_highest_spending_users_redis`, stockez le rapport dans le cache avant de le retourner au contrôleur :
```python
r.hset('reports:highest_spending_users', mapping=result)
r.expire("reports:highest_spending_users", 60) # invalider le cache toutes les 60 secondes
return result
```

Au début de la méthode `get_highest_spending_users_redis`, vérifiez si le rapport existe déjà dans le cache. Si c'est le cas, retournez immédiatement l'objet en cache. Sinon, exécutez les étapes nécessaires pour générer le rapport :
```python
report_in_cache = r.hgetall("reports:highest_spending_users")
if report_in_cache:
    return json.loads(report_in_cache)
else:
    # Obtenir les clés des commandes 
    # Générer le rapport 
    # Trier (décroissant), limite X
    return result
```

Également, appliquez cette optimisation au rapport `best_selling_products`.

### 10. Testez la charge encore une fois
Reconstruisez et puis redémarrez le conteneur Docker.
```bash
docker compose down -v && docker compose up -d --build                     
```

Relancez les tests Locust avec les mêmes paramètres de la dernière activité. Si nécessaire, augmentez progressivement le nombre d'utilisateurs jusqu'à ce que l'application échoue.

> 💡 **Question 4** : À partir de combien d'utilisateurs votre application cesse-t-elle de répondre correctement (avec Redis + optimisation) ? Quelle est la latence et le taux d'erreur observés ? Illustrez votre réponse à l'aide des graphiques Locust.

### 11. Testez l'équilibrage de charge (load balancing) avec Nginx
Pour tester le scénario suivant, utilisez le répertoire `load-balancer-config` :
- Copiez le texte dans `docker-compose-to-copy-paste.txt` et collez-le dans `docker-compose.yml`
- Créez un fichier `nginx.conf` dans le répertoire racine du projet.
- Copiez le texte dans `nginx-conf-to-copy-paste.txt` et collez-le dans un fichier `nginx.conf`
Observez les modifications apportées à `docker-compose.yml`. Ensuite, reconstruisez et puis redémarrez le conteneur Docker.
```bash
docker compose down -v && docker compose up -d --build                     
```

Relancez les tests Locust avec les mêmes paramètres de la dernière activité.

> 💡 **Question 5** : À partir de combien d'utilisateurs votre application cesse-t-elle de répondre correctement (avec Redis + Optimisation + Nginx load balancing) ? Quelle est la latence moyenne (50ème percentile) et le taux d'erreur observés ? Illustrez votre réponse à l'aide des graphiques Locust.

> 💡 **Question 6** : Avez-vous constaté une amélioration des performances à mesure que nous avons mis en œuvre différentes approches d'optimisation ? Quelle a été la meilleure approche ? Justifiez votre réponse en vous référant aux réponses précédentes.

> 💡 **Question 7** : Dans le fichier `nginx.conf`, il existe un attribut qui configure l'équilibrage de charge. Quelle politique d'équilibrage de charge utilisons-nous actuellement ? Consultez la documentation officielle Nginx si vous avez des questions.

## 📦 Livrables

- Un fichier .zip contenant l'intégralité du code source du projet Labo 04.
- Un rapport en .pdf répondant aux questions présentées dans ce document. Il est obligatoire d'illustrer vos réponses avec du code ou des captures d'écran/terminal.
