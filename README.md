# Intro
This program is a simple implementation of a simple online game. I tried to code it in under 8 hours which means I had to cut some corners. The "Discussion" section of this document goes into more depth about the tradeoffs I had to make.  
# Dev Environment Setup
This app is written for Python 3.6.3. Create a virtual environment and install the dependencies in `requirements-dev.txt`.  
Now, run database migrations: `python manage.py migrate`.   
Then, import fixtures: `python manage.py import_fixtures`. Now, you have a user with username "test-user" and password "PassworD" with 100 units of money in the user's real money wallet.  
Finally, run the dev server: `python manage.py runserver`.   
Visist `localhost:8000` to see the login page.   
# Discussion
## The Focus of This Solution
Time was limited so I decided to focus on creating a solution that   
- Meets the requirements  
- Has a simple architecture  
- Persists every monetary transaction (more on this below)  
- Is easy to extend in future (more on this below)  

### Persistance of Every Transaction
The online gambling business is heavily regulated. So, I think it's important that every event involving money should be persisted. In this application such events are called a `Transaction` and get persisted.  
### Easily Extending the Application
The requirements mention that it should be easy to add new bonus criteria. I've tried to minizmie the number of modifications needed to add new types of bonuses.    
Adding a new bonus type involves creating a new row in the `BonusType` table and adding the corresponding logic. None of the existing bonus types and their logic need to be modified unless the logic of the new bonus conflicts with the existing ones.   
### `Transaction`
Since giving a bonus involves money it is treated as a `Transaction`. Other types of `Transaction`s are:   
- user depositing money into their wallet  
- user winning or losing a game  


Future `Transaction` types can be added without having to do complex database migrations. The reason for this is that `Transaction` is a generic type. It has a one-to-one relationship with specific transaction types like `BonusTransaction`. This means that to create a new type of transaction like `DepositTransaction`, I just create a new table with that name. This transaction type(and database table) will be totally independent of other transaction types(and database tables).  
## What's Bad About This Solution

I had to do away with best practices at every level from architecture till code style. Basically, the production version of this app would look and operate totally differently. But, there are a few interesting points I'd like to make.
### Transactions
I'm not sure about the `Transaction` abstraction. I came up with it after experimenting with two other ideas.   
### Relational Abstractions
Something I definitely would do given more time is prototyping with a NoSQL or object database. Documents seem to be better fit for things like `Wallet`s in this application.   
### Race Conditions
There are several situations in this application where race conditions can appear. They all have to do with manipulating `Wallet` rows. These race conditions usually call for locking or versioning rows, or serializing events so that concurrent events don't occur.   
Locking rows in SQLite is not possible. SQLite locks the whole table during write transactions. That's why I didn't use statements like `select_for_update`.    
### Database Load
Some of the operations(e.g. does user have enough moeney to play the game?) on the `Wallet` table require traversing through wallets and transactions. This can quickly get out of control when there's a large number of users and transactions. My solution is to cache each wallet's current balance in the `Wallet` table. Redis or memcached might be better tools for this purpose.  
Another issue is my use of transactions in pretty much every usecase(e.g. deposit money, deduct money, reward user with bonus). The weakness of this approach, when using PostgreSQL or MySQL, can be that I'm locking rows a lot. Although most of the locked rows are new rows(i.e. they're not going to be used by other transactions) existing `Wallet` rows do get locked.    
### Architecture
Turning this solution into a monolith can be challening especially if new types of games are introduced. One way to prevent this would be to break the application down into smaller pieces. For example, I would separate the logic of playing games from things like user profile, statistics, or history of events.   
### Known Bugs or Missing Fixes
- If you deposit more than 999 a `decimal.InvalidOperation` exception occurs.  
- I'm not handling exceptions caused by failing database transactions. Such exceptions would cause 500 errors.  
- I don't have any tests for the views. Also, the handling of bonuses is not fully tested.  
- I've not specified the currency of transactions or money anywhere in this application.  

### Update
- I'm using a redis mock to keep track of how much money user spends and wagers. This mock has an API very similar to `redis-py`.
- Since there's no redis, none of the guarantees and benefits of redis(e.g. atomicity, concurrency control, speed) are present in this solution.
- The wager requirement is the same for all bonuses(10)
- The wager requirement is saved for all `wallet` rows even real money ones which don't need it. This is not good practice.
- There are a few circular imports that I've fixed temporarily in a hacky way.
- There could be potential race conditions in `transfer_eligible_bonuses_to_real_money_wallet` function if user takes concurrent or fast actions that affect `wallet` rows. I tried to mitigate most of the issues, but not all potential race conditions are dealt with.
- The new feature(automatic wagering) is well-tested but I didn't manually test the webpage to see if the new feature can throw 500 errors.
- I think one of the best ways to deal with concurrency control issues in this application is to serialize user's actions. We can lock user's wallets and even explicity tell the user not to use the system concurrently. Or, we can give the impression that concurrent games are possible when we actually queue user actions in the backend.
