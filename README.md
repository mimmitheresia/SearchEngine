# DD2476 Project

## Dataset
The search engine uses [this](https://www.kaggle.com/shivamb/netflix-shows/tasks?taskId=116) dataset from kaggle as its basis. It consists of ~7700 netflix titles.

## Environment
The application requires elasticsearch to be running. For simplicity the movie dataset can be loaded through Kibana. Thus, make sure you have the following setup:

```
elasticsearch (we used version 7.12.1)
kibana (we used version 7.12.1)
```

### Loading the dataset
In order to load the dataset into elasticsearch, do the following: 
1. Open Kibana
2. Press Upload a file on the front page
3. Select the csv file
4. Press import
5. Name the index `netflix` and press import
6. It will say that some documents could not be imported, don't worry about that

Now the index is ready to be queried from the user interface

## Dependencies
The application is built using python 3.8 and it requires the following dependecies to run:
```
tkinter (installation instructions below)
tinydb (pip install tinydb)
```

### Installing tkinter
[Instructions here](https://tkdocs.com/tutorial/install.html)

## Database
The project uses tinydb which stores its data in json file. We store the user profiles there and feel free to use our pre-made users or create one yourself. Either way the code assumes the database is located at `./db/users.json`.

## Running the interface
When all dependencies are installed, the application can be run with the following command:

```
python main.py
```

If you want to start with an empty user intead of using the ones we've created run the following command:
```
rm ./db/users.json && python add_person.py
```

## The user interface

The user interface is fairly simple, at the top you will find a list of the users and whenevery you run a query or select a title a user has to be selected. Below that list is the input box, where you can enter a query and search. Below the input are the results and at the bottom of the page is the search history and previous selections made by the user.


