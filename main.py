from tkinter import Tk, Label, Button, Entry, StringVar, Listbox
from elasticsearch import Elasticsearch
from tinydb import TinyDB, Query
from datetime import datetime
from statistics import stdev

users_db = TinyDB('./db/users.json')

es = Elasticsearch()


def get_dsl(query, functions):
    return {
        "size": 100,
        "query": {
            "function_score": {
                "query": {
                    "multi_match": {
                        "query": query,
                        "type": "best_fields",
                        "fields": ["title", "description", "cast", "director"]
                    }
                },
                "boost": 10,
                "functions": functions,
                "score_mode": "multiply",
                "boost_mode": "multiply"
            }
        }
    }


class SearchGUI:

    def update_db(self):
        for user in self.users_dict.values():
            Q = Query()
            users_db.update(user, Q.user_id == user['user_id'])

    def add_user_history(self, index, history):
        self.users_dict[index]['history'].append(history)
        self.update_db()

    def add_user_selection(self, index, selection):
        self.users_dict[index]['selections'].append(selection)
        self.update_db()

    def get_selected_user(self):
        selection = self.users_listbox.curselection()
        if len(selection) > 0:
            index = selection[0]
            return index, self.users_dict[index]
        elif self.results_user is not None:
            return self.results_user, self.users_dict[self.results_user]
        else:
            return None, None

    def selections_release_year_function(self):
        index, user = self.get_selected_user()
        if index is not None and user is not None:
            years = []
            selections = user['selections']
            if len(selections) <= 0:
                return []
            for selection in selections:
                source = selection['_source']
                years.append(source['release_year'])
            return [{
                "exp": {
                    "release_year": {
                        "origin": sum(years) / len(years),
                        "offset": 2,
                        "scale": stdev(years),
                        "decay": 0.5
                    }
                },
                "weight": 1
            }]
        else:
            return []

    def selections_description_function(self):
        index, user = self.get_selected_user()
        if index is not None and user is not None:
            descriptions = []
            selections = user['selections']
            if len(selections) <= 0:
                return []
            for selection in selections:
                source = selection['_source']
                descriptions.append(source['description'])
            desc = ' '.join(descriptions)
            return [{
                "filter": {
                    "match": {
                        "description": {
                            "query": desc,
                            "auto_generate_synonyms_phrase_query": True
                        }
                    }
                },
                "weight": 2
            }]
        else:
            return []

    def history_function(self):
        index, user = self.get_selected_user()
        if index is not None and user is not None:
            if user['user_id'] < 0:
                return []
            queries = []
            history = user['history']
            if len(history) <= 0:
                return []
            for entry in history:
                queries.append(entry['query'])
            tmp = ' '.join(queries)
            return [{
                "filter": {
                    "multi_match": {
                        "query": tmp,
                        "type": "best_fields",
                        "fields": ["title", "description", "cast", "director"]
                    }
                },
                "weight": 1
            }]
        else:
            return []

    def selections_listed_in_functions(self):
        index, user = self.get_selected_user()
        if index is not None and user is not None:
            selections = user['selections']
            if len(selections) <= 0:
                return []
            listed_in = dict()
            nbr_selections = len(selections)
            for selection in selections:
                source = selection['_source']
                categories = source['listed_in'].split(', ')
                for category in categories:
                    if category in listed_in:
                        listed_in[category] = listed_in.get(category) + 1
                    else:
                        listed_in[category] = 1
            return [{
                "filter":
                    {"match_phrase":
                        {
                            "listed_in": c
                        }
                    },
                "weight": (listed_in[c] / nbr_selections) * 4
            } for c in listed_in.keys()]
        else:
            return {}

    def selections_type_functions(self):
        index, user = self.get_selected_user()
        if index is not None and user is not None:
            selections = user['selections']
            if len(selections) <= 0:
                return []
            movies = 0
            tv_shows = 0
            nbr_selections = len(selections)
            for selection in selections:
                source = selection['_source']
                category = source['type']
                if category == 'Movie':
                    movies += 1
                else:
                    tv_shows += 1
            if movies > tv_shows:
                movies_percentage = movies / (movies + tv_shows)
                if movies_percentage > 0.75:
                    return [{
                        "filter": {
                            "match": {
                                "type": 'Movie'
                            }
                        },
                        "weight": movies_percentage * 2
                    }]
            else:
                tv_shows_percentage = tv_shows / (movies + tv_shows)
                if tv_shows_percentage > 0.75:
                    return [{"filter": {"match": {"type": 'TV Show'}}, "weight": tv_shows_percentage * 2}]
        return []

    def search(self, query):
        index, user = self.get_selected_user()
        if index is not None and user is not None:

            functions = self.selections_listed_in_functions() \
                        + self.selections_type_functions() \
                        + self.selections_release_year_function() \
                        + self.selections_description_function() \
                        + self.history_function()
            self.error_message.set("")
            body = get_dsl(query, functions)
            # print(body)
            response = es.search(body=body, index="netflix")
            hits = response['hits']['hits']
            timestamp = datetime.now().timestamp()
            self.add_user_history(index, {'timestamp': timestamp, 'query': query})
            self.update_result(index, hits)
            self.update_shown_profile()
        else:
            self.error_message.set("select a user before searching")

    def update_result(self, index, results):
        nbr_items = self.result_listbox.size()
        self.result_listbox.delete(0, nbr_items)
        self.results_user = index
        self.results.clear()
        for index, result in enumerate(results):
            source = result['_source']
            score = float(result['_score'])
            self.results.insert(index, result)
            # self.result_listbox.insert(index, "%.3f \t %s \t %s \t %s"%(score, str(source['release_year']), source['title'], source['listed_in']))
            self.result_listbox.insert(index, "%s \t %s \t\t %s \t %s \t %s"% (source['release_year'], source['type'],
                                                                                source['title'], source['description'],
                                                                                     source['listed_in']))
            if index < 20:
                print("%s \t %s \t %s \t %s \t %s" % (
                    source['title'], source['type'], source['release_year'], source['listed_in'],
                    source['description']))

    def update_shown_profile(self):
        index, user = self.get_selected_user()
        if index is not None and user is not None:
            nbr_history = self.history_listbox.size()
            self.history_listbox.delete(0, nbr_history)
            for index, result in enumerate(user['history']):
                self.history_listbox.insert(index, "%s \t\t %s" % (result['timestamp'], result['query']))

            nbr_selections = self.selections_listbox.size()
            self.selections_listbox.delete(0, nbr_selections)
            for index, result in enumerate(user['selections']):
                source = result['_source']
                self.selections_listbox.insert(index, "%s \t %s \t\t %s \t %s \t %s"% (source['release_year'], source['type'],
                                                                                source['title'], source['description'],
                                                                                     source['listed_in']))

    def select(self):
        selection = self.result_listbox.curselection()
        user_index = self.results_user
        if len(selection) > 0 and user_index is not None:
            item = self.results[selection[0]]
            self.add_user_selection(user_index, item)
            self.update_shown_profile()
        else:
            self.error_message.set("perform a search first")

    def update_users(self):
        users = users_db.all()
        nbr_items = self.users_listbox.size()
        self.users_listbox.delete(0, nbr_items)
        for index, result in enumerate(users):
            self.users_dict[index] = result
            self.users_listbox.insert(index, "%s \t\t %s" % (result['user_id'], result['name']))

    def __init__(self, master):
        self.master = master
        master.title("Search engine")

        self.users_dict = dict()

        self.results_user = None
        self.results = list()

        self.users_listbox = Listbox(self.master, selectmode="SINGLE", width=200)
        self.users_listbox.grid(column=0, row=0, columnspan=10)

        self.update_users()
        self.users_listbox.activate(0)

        self.query = StringVar()
        self.entry = Entry(self.master, textvariable=self.query, width=160)
        self.entry.grid(column=0, row=1, columnspan=10)

        Button(self.master, command=lambda: self.search(self.query.get()), text="Search", width=20).grid(column=0,
                                                                                                         row=2,
                                                                                                         columnspan=10)

        Label(self.master, text="Results").grid(column=0, row=3, columnspan=10)
        self.result_listbox = Listbox(self.master, selectmode="SINGLE", width=200)
        self.result_listbox.grid(column=0, row=4, columnspan=10)

        Button(self.master, command=lambda: self.select(), text="Select", width=40).grid(column=0,
                                                                                         row=5,
                                                                                         columnspan=10)

        Label(self.master, text="History").grid(column=0, row=6, columnspan=5)
        self.history_listbox = Listbox(self.master, selectmode="SINGLE", width=100)
        self.history_listbox.grid(column=0, row=7, columnspan=5)

        Label(self.master, text="Selections").grid(column=5, row=6, columnspan=5)
        self.selections_listbox = Listbox(self.master, selectmode="SINGLE", width=100)
        self.selections_listbox.grid(column=5, row=7, columnspan=5)

        self.error_message = StringVar()
        Label(self.master, textvariable=self.error_message, fg="red").grid(column=0, row=8, columnspan=10)


# users_db.insert({'user_id': 100, 'name': 'TV-show buff', 'history': [], 'selections': []})
# users_db.insert({'user_id': 200, 'name': 'Attenboroughfan', 'history': [], 'selections': []})
# users_db.insert({'user_id': 300, 'name': '90sNostalgia', 'history': [], 'selections': []})
# users_db.insert({'user_id': 400, 'name': 'Bollywoodlover', 'history': [], 'selections': []})
# users_db.insert({'user_id': -100, 'name': 'Unidentified Stranger', 'history': [], 'selections': []})


root = Tk()
gui = SearchGUI(root)
root.mainloop()
