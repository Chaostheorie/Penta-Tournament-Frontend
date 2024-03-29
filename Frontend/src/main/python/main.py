from fbs_runtime.application_context.PyQt5 import ApplicationContext
from simplejson.errors import JSONDecodeError
from PyQt5 import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *

import requests  # API requests
import sys
import time
import logging
import json  # JSON handling


class CredentialsExption(Exception):
    """For Authentication failure by Server connection"""
    pass


class AuthorizationException(Exception):
    """Exception raised by unauthorized access 'Some permissions missing?'"""
    pass


class APIException(Exception):
    """Exception for server side Errors 'They fucked up'"""
    pass


class ClientException(Exception):
    """Exceptions for APIBIND Errors 'You fucked up'"""


class APIBIND:
    def __init__(self, url, port, protocol, username=None, password=None):
        self.session = requests.session()
        self.url = protocol + "://" + url + ":" + str(port) + "/api/"
        if username is not None and password is not None:
            self.connect(username, password)
            self.username = username

    def connect(self, username, password):
        self.auth = requests.auth.HTTPBasicAuth(username=username,
                                                password=password)
        r = self.session.get(f"{self.url}user/token", auth=self.auth)
        if r.status_code != 200:
            raise CredentialsExption("Password or Username is Wrong")
        try:
            r = r.json()
            logging.debug(f"ID: {r['id']}")
            logging.debug(f"TOKEN: {r['token']}")
            logging.debug(f"TOKEN: {r['refresh_token']}")
            self.token = r["token"]
            self.id = r["id"]
            self.refresh_token = r["refresh_token"]
        except JSONDecodeError:
            raise APIException("Server Response Invalid")

    def renew_token(self):
        payload = {"refresh_token": self.refresh_token, "password": None}
        r = self.request("user/token", payload, renew=False,
                         credentials=False, refresh=False, method="GET")
        if r.status_code == 400:
            pass
        elif r.status_code == 401:
            raise APIException("The authentication is buggy")
        r = r.json()
        self.token = r["token"]
        self.refresh_token = r["refresh_token"]

    def sign_up(self, username, password):
        payload = {"username": username, "password": password}
        return self.request("user/sign-up", payload, credentials=False)

    def parse_list(self, r):
        try:
            return [json.loads(chunk) for chunk in r.json()]
        except TypeError:
            logging.warning("JSON was not processable, passing r.json()")
            return r.json()
        except JSONDecodeError:
            raise APIException("JSON List was invalid")

    def get_tournament_games(self, id, duo=False, stringify=False,
                             ongoing=False, limit=None, load_players=False):
        """Get games related to tournamentspayload
           Note: duo allows double output with stringify"""
        payload = dict(limit=limit, ongoing=ongoing, load_players=load_players)
        r = self.request(f"tournament/{id}/games", payload, "GET")
        if stringify:
            if duo:
                return self.game_stringify(self.parse_list(r)
                                           ), self.parse_list(r)
            return self.game_stringify(self.parse_list(r))
        else:
            return self.parse_list(r)

    def create_tournament(self, name, duration, date,
                          description, participants):
        paylod = dict(name=name, duration=duration, description=description,
                      participants=participants,
                      date=date.toString(Qt.ISODate))
        return self.request("tournaments/create", paylod, "POST")

    def game_stringify(self, games, ongoing=False):
        results = []
        for data in games:
            if isinstance(data, list):
                logging.warning("Game stringify can't handle nested lists")
                break
            res = data["date"]
            res += " "*5
            if data["active"]:
                res += "Running"
                res += " "*5
            res += str(len(data["result"]))
            if len(data["result"]) != 5:
                res += " "*(6-len(data["result"]))
            else:
                ree += " "*1
            if len(data["result"]) == 1:
                res += "player"
            else:
                res += "players"
            results.append(res)
        return results

    def get_user_games(self, limit=10, stringify=False):
        """Get games """
        return

    def get_players(self, limit=100):
        """Gets list of players"""
        payload = {"limit": limit}
        r = self.request("user/list", payload, "GET")
        return self.parse_list(r)

    def get_leaderboard(self, down_to=100):
        payload = {"down_to": down_to}
        r = self.request("user/leaderboard", payload, "GET")
        return self.parse_list(r)

    def get_tournaments(self, personal=True, active=True,
                        stringify=False, duo=False):
        if active:
            payload = {"limit": 10}
            if personal:
                payload["maintainer_id"] = self.id
            r = self.request("tournaments/ongoing", payload, "GET")
        else:
            payload = {"limit": 10}
            if personal:
                payload["maintainer_id"] = self.id
            r = self.request("tournaments/list", payload, "GET")
        if stringify:
            tournaments, results = self.tournament_stringify(self.parse_list(r),
                                                             source=True)
            if duo:
                return results, tournaments
            else:
                return results
        else:
            return self.parse_list(r)

    def tournament_stringify(self, tournaments, source=False):
        results = []
        for data in tournaments:
            if len(data["name"]) < 50:
                res = data["name"] + " "*(51-len(str(data["name"])))
            else:
                res = data["name"] + " "
            if data["active"] is True:
                res += "active   "
            else:
                res += "inactive "
            if data["participants"] < 5:
                res += str(data["participants"])
                res += " "*(5-len(str(data["participants"])))
            else:
                res += str(data["participants"])
            res += " participants"
            results.append(res)
        if source:
            return tournaments, results
        return results

    def get_changelog(self):
        changelog = self.request("gui/changelog", method="GET")
        return changelog.text

    def request(self, endpoint, payload=[], method="POST",
                credentials=True, refresh=True, renew=True):
        if credentials and (method != "GET") and payload != []:
            auth = True
        else:
            auth = False
        payload = json.dumps(payload)
        url = self.url + endpoint
        if method == "POST":
            if not auth:
                r = self.session.post(url, data=payload)
            else:
                r = self.session.post(url, data=payload, auth=self.auth)
        elif method == "PUT":
            if not auth:
                r = self.session.put(url, payload)
            else:
                r = self.session.put(url, payload, auth=self.auth)
        elif method == "GET":
            if not auth:
                r = self.session.get(url, params=payload)
            else:
                r = self.session.get(url, params=payload, auth=self.auth)
        elif method == "DELETE":
            if not auth:
                r = self.session.delete(url, payload)
            else:
                r = self.session.delete(url, payload, auth=self.auth)
        else:
            raise APIException(f"Method '{method}' not allowed")
        if r.status_code != 200:
            if r.status_code == 401:
                if renew:
                    self.renew_token()
            elif r.status_code == 404:
                raise APIException(f"endpoint '{endpoint}' not found")
            elif r.status_code == 403:
                raise AuthorizationException(f"You're Not allowed to \
                                                access {endpoint}")
            elif r.status_code == 500:
                raise APIException("Server Side Error - Report was send")
            elif r.status_code == 503:
                raise APIException("Server is down for maintainece or high load")
            elif r.status_code == 401:
                raise CredentialsExption("User not logged in")
            else:
                return r
        return r


class ConfigError(Exception):
    pass


class Config:
    def __init__(self, config_file, use_args=True, auto_update=True,
                 supported_enviroments=["default", "experimental", "custom"]):
        """Config object for handling with config file"""
        self.config_file = config_file
        self.auto_update = auto_update
        self.supported_enviroments = supported_enviroments
        with open(config_file) as f:
            self.raw = json.load(f)
        if use_args and ("-e" in sys.argv or "--experimental" in sys.argv):
            self.use_experimental = True
            self.enviroment = "experimental"
        elif use_args and ("-c" in sys.argv or "--custom" in sys.argv):
            self.use_experimental = True
            self.enviroment = "custom"
        elif use_args is False:
            try:
                self.raw["enviroment"]
            except KeyError:
                raise ConfigError("Config file Broken - Repair recommended")
        else:
            self.use_experimental = False
            self.enviroment = "default"
        if "-d" in sys.argv or "--debug" in sys.argv:
            logging.basicConfig(level=logging.DEBUG)
        elif "-i" in sys.argv or "--info" in sys.argv:
            logging.basicConfig(level=logging.INFO)

    def __getitem__(self, key):
        """Gets item by key from config_file and enviroment"""
        try:
            return self.raw[self.enviroment + "-config"][key]
        except KeyError:
            raise ConfigError("Requested key was not in config")

    def __setitem__(self, key, val):
        """Sets a config setting and updates config if auto_update enabled"""
        self.raw[self.enviroment][key] = val
        if self.auto_update:
            try:
                with open(self.config_file, "w") as f:
                    json.dump(self.raw)
            except PermissionError:
                raise ConfigError("Config File is missing write permissions")
        logging.debug(f"Key '{key}' assigned '{value}'")

    def load_config(self):
        """Loads config from config_file arg (self.config_file)"""
        try:
            with open(self.config_file) as f:
                self.raw = json.load(f)
        except PermissionError:
            raise ConfigError("Config File is missing read permissions")
        logging.info("Config loaded")

    def __contains__(self, value):
        """Checks if key is in current config enviroment"""
        if value in self.raw[self.enviroment]:
            return True
        else:
            return False

    def set_enviroments(self, enviroment):
        if enviroment in self.supported_enviroments:
            self.enviroment = enviroment
            logging.debug(f"Enviroment changed to '{enviroment}'")
        else:
            raise ConfigError("Enviroment not supported or properly passed")

    def reset_config(self):
        template_path = self.config_file[:self.config_file.rfind("/")]
        template_path += "/templates/preferences.json"
        logging.info(f"Config is reseted with file from {template_path}")
        with open(templates_path) as f:
            template = json.load(f)
        with open(self.config_file, "w") as f:
            json.dump(f)
        logging.debug(f"template: \n {template}")


class QTournamentItem(QTableWidgetItem):
    def __init__(self, id, *args, **kwargs):
        self.id = id
        super().__init__(*args, **kwargs)
        logging.debug(f"QTournamentItem <{id}> created")


class QPlayerItem(QStandardItem):
    def __init__(self, id, *args, **kwargs):
        self.id = id
        super().__init__(*args, **kwargs)
        logging.debug(f"QPlayerItem <{id}> created")


class QGameItem(QTableWidgetItem):
    def __init__(self, id, result, *args, **kwargs):
        self.id = id
        self.result = result
        super().__init__(*args, **kwargs)
        logging.debug(f"QGameItem <{id}> created")


class PentaTournament(ApplicationContext):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with open(self.get_resource("banner.txt")) as f:
            print(f.read())
        self.app.setStyleSheet(open(self.get_resource('style.qss')).read())
        self.config = Config(self.get_resource("preferences.json"),
                             use_args=True, auto_update=False)
        self.load_palette()
        self.api = APIBIND(url=self.config["server-url"],
                           protocol=self.config["protocol"],
                           port=self.config["port"])
        self.connect()

    def connect(self):
        self.log_in = QWidget()
        self.log_in.resize(600, 25)
        self.log_in.setWindowTitle("Log In")
        self.log_in_layout = QGridLayout()
        self.username = QLineEdit(parent=self.log_in)
        self.username.setPlaceholderText("Username")
        self.password = QLineEdit(parent=self.log_in)
        self.password.setPlaceholderText("Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.log_in_button = QPushButton("Log In", parent=self.log_in)
        self.sign_up_connect_button = QPushButton("Sign up",
                                                  parent=self.log_in)
        StyleSheet = "QPushButton {color: white}"
        self.log_in_button.setStyleSheet(StyleSheet)
        self.sign_up_connect_button.setStyleSheet(StyleSheet)
        self.log_in_button.setShortcut("Return")
        self.log_in_button.clicked.connect(self._connect)
        self.sign_up_connect_button.clicked.connect(self.Sign_up)
        qr = self.log_in.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.log_in.move(qr.topLeft())

        self.log_in_layout.addWidget(self.log_in_button, 3, 0)
        self.log_in_layout.addWidget(self.sign_up_connect_button, 3, 1)
        self.log_in_layout.addWidget(self.username, 1, 0, 1, 2)
        self.log_in_layout.addWidget(self.password, 2, 0, 1, 2)
        self.username.setDisabled(False)
        self.password.setDisabled(False)
        self.log_in.setLayout(self.log_in_layout)
        self.log_in.show()
        self.username.setFocusPolicy(Qt.StrongFocus)
        self.username.setFocus()
        logging.debug("Login Window created")
        return

    def _connect(self):
        try:
            self.api.connect(username=self.username.text(),
                             password=self.password.text())
            logging.debug("Authentication sucessfull")
            self._username = self.username.text()
            self.log_in.close()
            self.create_fronted()
        except CredentialsExption:
            self.alert("Username or Password is wrong")
            self.password.setText("")
        except APIException:
            error = """
            Server Seems to be sending faulty responses
            Please Check your Network Connection or the Backend server
            If the issue is server side related, please create an realted issue
            """
            self.alert(error)

    def create_fronted(self):
        self.main_widget = QWidget()
        self.main_window = QMainWindow(parent=self.main_widget)
        self.home_btn = QPushButton()
        self.home_btn.minimumSize()
        self.home_btn.setIcon(QIcon(self.get_resource("inapp.svg")))
        self.home_btn.setMinimumSize(QSize(48, 64))
        self.home_btn.setFixedWidth(48)
        StyleSheet = """QPushButton {border: solid;
                                    background-color: lightgreen; padding: 0px;
                                     }"""
        self.home_btn.setStyleSheet(StyleSheet)
        self.tournament_btn = QPushButton()
        self.tournament_btn.setIcon(QIcon(self.get_resource("tournaments.svg")
                                          ))
        StyleSheet = """QPushButton {border: solid;
                                     background-color: lightgray;
                                     padding: 0px;
                                     }"""
        self.tournament_btn.setStyleSheet(StyleSheet)
        self.tournament_btn.setMinimumSize(QSize(48, 64))
        self.tournament_btn.setMaximumWidth(48)
        self.tournament_manage_btn = QPushButton()
        self.tournament_manage_btn.setIcon(QIcon(self.get_resource("manager.svg")))
        self.tournament_manage_btn.setStyleSheet(StyleSheet)
        self.tournament_manage_btn.setMinimumSize(QSize(48, 64))
        self.leaderboard_btn = QPushButton()
        self.leaderboard_btn.setIcon(QIcon(self.get_resource("podium.svg")))
        self.leaderboard_btn.setStyleSheet(StyleSheet)
        self.leaderboard_btn.setMinimumSize(QSize(48, 64))
        self.leaderboard_btn.setMaximumWidth(48)
        self.announcmentes_btn = QPushButton()
        self.announcmentes_btn.setIcon(QIcon(self.get_resource("announcments.svg")))
        self.announcmentes_btn.setStyleSheet(StyleSheet)
        self.announcmentes_btn.setMinimumSize(QSize(48, 64))
        self.announcmentes_btn.setMaximumWidth(48)

        self.home_btn.clicked.connect(self.button1)
        self.tournament_btn.clicked.connect(self.button2)
        self.leaderboard_btn.clicked.connect(self.button3)
        self.announcmentes_btn.clicked.connect(self.button4)
        self.tournament_manage_btn.clicked.connect(self.button5)

        # add tabs
        self.tab1 = self.home()
        self.tab2 = self.tournaments()
        self.tab3 = self.leaderboards()
        self.tab4 = self.announcmentes()
        self.tab5 = self.tournament_manage()
        left_layout = QVBoxLayout()
        left_layout.setAlignment(Qt.AlignTop)
        left_layout.addWidget(self.home_btn)
        left_layout.addWidget(self.tournament_btn)
        left_layout.addWidget(self.leaderboard_btn)
        left_layout.addWidget(self.announcmentes_btn)
        left_layout.addWidget(self.tournament_manage_btn)
        left_layout.addStretch(5)
        left_layout.setSpacing(0)
        left_layout.setContentsMargins(QMargins(0, 0, 0, 0))
        left_widget = QWidget()
        left_widget.setLayout(left_layout)
        left_widget.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        self.right_widget = QTabWidget()
        self.right_widget.tabBar().setObjectName("mainTab")

        self.right_widget.addTab(self.tab1, "")
        self.right_widget.addTab(self.tab2, "")
        self.right_widget.addTab(self.tab3, "")
        self.right_widget.addTab(self.tab4, "")
        self.right_widget.addTab(self.tab5, "")

        self.right_widget.setCurrentIndex(0)
        self.right_widget.setStyleSheet('''QTabBar::tab{width: 0; \
            height: 0; margin: 0; padding: 0; border: none;}''')
        self.right_widget.setSizePolicy(QSizePolicy.Expanding,
                                        QSizePolicy.Expanding)

        main_layout = QGridLayout()
        left_widget.setFixedWidth(self.home_btn.size().width())
        main_layout.addWidget(left_widget, 0, 0)
        main_layout.addWidget(self.right_widget, 0, 1)
        main_layout.setSpacing(0)
        self.frontend = QWidget()
        self.frontend.setLayout(main_layout)
        self.main_window.setCentralWidget(self.frontend)
        self.main_window.showMaximized()
        logging.debug("Main Window Created")

    def button1(self):
        self.update_home()
        self.right_widget.setCurrentIndex(0)
        logging.debug("Home selected")

    def button2(self):
        self.update_tournaments()
        self.right_widget.setCurrentIndex(1)
        logging.debug("Tournaments overview selected")

    def button3(self):
        self.update_leaderboard()
        self.right_widget.setCurrentIndex(2)
        logging.debug("Leaderboard selected")

    def button4(self):
        self.right_widget.setCurrentIndex(3)
        logging.debug("announcments selected")

    def button5(self):
        self.right_widget.setCurrentIndex(4)
        self.your_tournaments.clear()
        tournaments = self.api.get_tournaments(personal=True, active=False)
        self.your_tournaments.setColumnCount(3)
        self.your_tournaments.setRowCount(len(tournaments))
        columns = ["name", "maintainer_username", "date"]
        additions = ["", "Maintained by ", ""]
        for x in range(len(tournaments)):
            for i in range(len(columns)):
                cell_content = additions[i] + tournaments[x][columns[i]]
                cell = QTournamentItem(tournaments[x]["id"], cell_content)
                cell.setFlags(Qt.ItemIsEnabled)
                self.your_tournaments.setItem(x, i, cell)
        self.your_tournaments.setEditTriggers(QAbstractItemView.NoEditTriggers)
        logging.debug("Tournaments Manager selected")

    def clear_layout(self, layout):
        for i in reversed(range(layout.count())):
            layout.itemAt(i).widget().setParent(None)
        logging.debug(f"Layout <{layout}> cleared")
        return

    def update_home(self):
        return

    def tournament_focused(self, row, col):
        row = self.your_tournaments.item(row, col)
        self.ongoing_games.clear()
        games = self.api.get_tournament_games(row.id)
        self.ongoing_games.setRowCount(len(games))
        columns = [None, "date", "players", "state"]
        additions = ["Game", "", "Players: ", "State: "]
        logging.debug(f"Tournament <{row.id}> clicked")
        if games is None:
            return
        for x in range(len(games)):
            for i in range(len(columns)):
                if columns[i] is None:
                    cell_content = additions[i]
                else:
                    cell_content = additions[i] + str(games[x][columns[i]])
                cell = QGameItem(games[x]["id"], games[x]["result"],
                                 cell_content)
                cell.setFlags(Qt.ItemIsEnabled)
                self.ongoing_games.setItem(x, i, cell)

    def Tournament_double_clicked(self, row, col):
        return

    def game_focused(self, index):
        game = self.api.get_game(row.id)
        game_highligth = QWidget()
        game_highligth_layout = QBoxLayout()
        game_highligth_box = QGroupBox()
        game_highligth_box_layout = QGridLayout()
        game_highligth_box_layout.addWidget(QLabel())
        logging.debug(f"Game focused <{row.id}/{game['date']}>")
        game_widget = QWidget()
        game_widget.setWindowTitle(f"Game {game['id']} from {game['date']}")
        game_layout = QGridLayout()
        metadata_box = QGroupBox("Metadata")
        game_layout.addWidget()

    def tournament_manage(self):
        self.manage = QWidget()
        self.manage_layout = QGridLayout()
        self.your_tournaments_box = QGroupBox("Your Tournaments")
        self.your_tournaments_layout = QGridLayout()
        self.your_tournaments = QTableWidget()
        self.your_tournaments.verticalHeader().hide()
        hheader = self.your_tournaments.horizontalHeader()
        hheader.hide()
        self.your_tournaments.cellClicked.connect(self.tournament_focused)
        tournaments = self.api.get_tournaments(personal=True, active=False)
        self.your_tournaments.setColumnCount(3)
        self.your_tournaments.setRowCount(len(tournaments))
        hheader.setSectionResizeMode(QHeaderView.Stretch)
        columns = ["name", "maintainer_username", "date"]
        additions = ["", "Maintained by ", ""]
        for x in range(len(tournaments)):
            for i in range(len(columns)):
                cell_content = additions[i] + tournaments[x][columns[i]]
                cell = QTournamentItem(tournaments[x]["id"], cell_content)
                cell.setFlags(Qt.ItemIsEnabled)
                self.your_tournaments.setItem(x, i, cell)
        self.your_tournaments.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.your_tournaments_layout.addWidget(self.your_tournaments, 1, 0)
        manage_box = QGroupBox()
        manage_box.setTitle("")
        manage_box.setStyleSheet("QGroupBox {border:none;}")
        manage_box_layout = QHBoxLayout()
        self.create_tournament_btn = QPushButton("Create New")
        self.archived_tournaments_btn = QPushButton("View Archive")
        self.create_tournament_btn.clicked.connect(self.create_tournament)
        self.archived_tournaments_btn.clicked.connect(self.view_archived)
        StyleSheet = "QPushButton {color: white;}"
        self.create_tournament_btn.setStyleSheet(StyleSheet)
        self.archived_tournaments_btn.setStyleSheet(StyleSheet)
        manage_box_layout.addWidget(self.create_tournament_btn)
        manage_box_layout.addWidget(self.archived_tournaments_btn)
        manage_box.setLayout(manage_box_layout)
        self.your_tournaments_layout.addWidget(manage_box)
        self.your_tournaments_box.setLayout(self.your_tournaments_layout)
        self.manage_layout.addWidget(self.your_tournaments_box, 1, 0)
        self.ongoing_games = QTableWidget()
        self.ongoing_games.setColumnCount(4)
        hheader = self.ongoing_games.horizontalHeader()
        hheader.hide()
        self.ongoing_games.verticalHeader().hide()
        hheader.setSectionResizeMode(QHeaderView.Stretch)
        self.ongoing_games_box = QGroupBox("Ongoing Games")
        self.ongoing_games_layout = QVBoxLayout()
        self.ongoing_games.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.ongoing_games_layout.addWidget(self.ongoing_games)
        self.ongoing_games_box.setLayout(self.ongoing_games_layout)
        self.manage_layout.addWidget(self.ongoing_games_box, 1, 1)
        self.manage.setLayout(self.manage_layout)
        return self.manage

    def create_tournament(self):
        self.create_widget = QWidget()
        create_layout_left = QVBoxLayout()
        create_layout_rigth = QVBoxLayout()
        create_layout = QHBoxLayout()
        self.tournament_name = QLineEdit()
        self.tournament_name.setPlaceholderText("Name")
        self.tournament_description = QTextEdit()
        self.tournament_description.setPlaceholderText("Description")
        self.tournament_date = QDateEdit()
        self.tournament_duration = QLineEdit()
        self.tournament_duration.setPlaceholderText("Duration")
        self.tournament_duration.setValidator(QIntValidator(1, 120))
        self.tournament_participants = QListView()
        player_model = QStandardItemModel()
        for player in self.api.get_players(limit=None):
            item = QPlayerItem(player["id"], player["username"])
            item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            item.setData(QVariant(Qt.Checked), Qt.CheckStateRole)
            player_model.appendRow(item)
        self.tournament_participants.setModel(player_model)
        create_button = QPushButton("Create")
        create_button.setStyleSheet("QPushButton {color:white;}")
        create_button.clicked.connect(self._create_tournament)
        create_layout_left.addWidget(self.tournament_name)
        create_layout_left.addWidget(self.tournament_description)
        date_box = QGroupBox()
        date_box.setStyleSheet("QGroupBox {border:none;}")
        date_box_layout = QHBoxLayout()
        date_box_layout.addWidget(self.tournament_date)
        date_box_layout.addWidget(self.tournament_duration)
        date_box.setLayout(date_box_layout)
        create_layout_left.addWidget(date_box)
        create_layout_left.addWidget(create_button)
        create_layout_rigth.addWidget(self.tournament_participants)
        create_left_widget = QWidget()
        create_rigth_widget = QWidget()
        create_left_widget.setLayout(create_layout_left)
        create_rigth_widget.setLayout(create_layout_rigth)
        create_layout.addWidget(create_left_widget)
        create_layout.addWidget(create_rigth_widget)
        self.create_widget.setLayout(create_layout)
        qr = self.create_widget.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.create_widget.move(qr.topLeft())
        self.create_widget.show()
        self.create_widget.setFocusPolicy(Qt.StrongFocus)
        self.create_widget.setFocus()

    def _create_tournament(self):
        rows = self.tournament_participants.model().rowCount()
        participants = [self.tournament_participants.model().item(i).id
                        for i in range(rows)]
        self.api.create_tournament(name=self.tournament_name.text(),
                                   date=self.tournament_date.dateTime(),
                                   duration=self.tournament_duration.text(),
                                   description=self.tournament_description.toPlainText(),
                                   participants=participants)
        self.alert(f"Tournament '{self.tournament_name.text()}' created")
        self.create_widget.hide()
        self.main_widget.setFocus()
        self.tournament_manage_btn.click()
        return

    def view_archived(self):
        return

    def update_tournaments(self):
        self.clear_layout(self.to_layout)
        self.to_layout = QVBoxLayout()
        for tournament in self.api.get_tournaments():
            to_layout = QHBoxLayout()
            to_layout.addWidget(QLabel(tournament["name"]))
            to_layout.addWidget(QLabel(str(tournament["participants"]) + " participants"))
            to_layout.addWidget(QLabel(tournament["date"]))
            to_layout.addWidget(QLabel(f"Maintained by {tournament['maintainer_username']}"))
            to = QWidget()
            to.setLayout(to_layout)
            self.to_layout.addWidget(to)
        self.to.setLayout(self.to_layout)
        self.to.show()
        return

    def update_leaderboard(self):
        return

    def home(self):
        self.home_layout = QGridLayout()
        self.home_layout.addWidget(QLabel("Home"), 0, 1)
        self.home_layout.setContentsMargins(QMargins(0, 0, 0, 0))
        self.home = QWidget()
        self.home.setLayout(self.home_layout)
        return self.home

    def tournaments(self):
        self.to_layout = QVBoxLayout()
        self.to_layout.setSpacing(0)
        for tournament in self.api.get_tournaments():
            to_layout = QHBoxLayout()
            to_layout.addWidget(QLabel(tournament["name"]))
            to_layout.addWidget(QLabel(str(tournament["participants"]) + " participants"))
            to_layout.addWidget(QLabel(tournament["date"]))
            to_layout.addWidget(QLabel(f"Maintained by {tournament['maintainer_username']}"))
            to = QWidget()
            to.setLayout(to_layout)
            self.to_layout.addWidget(to)
        self.to = QWidget()
        self.to.setLayout(self.to_layout)
        return self.to

    def leaderboards(self):
        self.leaderboard_layout = QGridLayout()
        self.leaderboard_layout.addWidget(QLabel("Top 100 Players - Updated every 24 Hours"), 0, 1)
        data = self.api.get_leaderboard()
        self.leaderboard_tableWidget = QTableWidget()
        self.leaderboard_tableWidget.verticalHeader().hide()
        _columns = ["Place", "name", "Score", "Last Tournament"]
        columns = ["id", "points", "username"]
        self.leaderboard_tableWidget.setColumnCount(len(columns))
        self.leaderboard_tableWidget.setRowCount(len(data))
        self.leaderboard_tableWidget.setHorizontalHeaderLabels(columns)
        for x in range(len(data)):
            for i in range(len(columns)):
                cell = QTableWidgetItem(str(data[x][columns[i]]))
                cell.setFlags(Qt.ItemIsEnabled)
                self.leaderboard_tableWidget.setItem(x, i, cell)
        self.leaderboard_tableWidget.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.leaderboard_tableWidget.horizontalHeader().setStretchLastSection(True)
        self.leaderboard_layout.addWidget(self.leaderboard_tableWidget, 1, 1)
        self.leaderboard = QWidget()
        self.leaderboard.setLayout(self.leaderboard_layout)
        return self.leaderboard

    def announcmentes(self):
        self.announcmentes_layout = QGridLayout()
        changelog = QLabel(self.api.get_changelog())
        self.announcmentes_layout.addWidget(changelog, 1, 1)
        self.announcmentes = QWidget()
        self.announcmentes.setLayout(self.announcmentes_layout)
        return self.announcmentes

    def _sign_up(self):
        if self.username.text().strip() == "":
            self.alert("Username needs to be at least one char")
        if self.password.text() == self.password_retype.text():
            t = self.api.sign_up(self.username.text().strip(),
                                 self.password.text())
            if t.status_code == 400:
                self.alert("Username is already used")
            else:
                self.alert(f"{self.username.text()} Created sucessfully")

        else:
            self.alert("Passwords didn't match")

    def alert(self, text):
        alert = QMessageBox()
        alert.setText(text)
        alert.exec_()

    def Sign_up(self):
        if self.log_in.isVisible():
            self.log_in.close()
        self.sign_up = QWidget()
        self.sign_up.resize(600, 25)
        self.sign_up.setWindowTitle("Log In")
        self.sign_up_layout = QGridLayout()
        self.username = QLineEdit(parent=self.sign_up)
        self.username.setPlaceholderText("Username")
        self.password = QLineEdit(parent=self.sign_up)
        self.password.setPlaceholderText("Password")
        self.password_retype = QLineEdit(parent=self.sign_up)
        self.password_retype.setPlaceholderText("Retype Password")
        self.password.setEchoMode(QLineEdit.Password)
        self.password_retype.setEchoMode(QLineEdit.Password)
        self.sign_up_button = QPushButton("Sign up", parent=self.sign_up)
        self.log_in_connect_button = QPushButton("Log in", parent=self.sign_up)
        StyleSheet = "QPushButton {color: white}"
        self.sign_up_button.setStyleSheet(StyleSheet)
        self.log_in_connect_button.setStyleSheet(StyleSheet)
        self.sign_up_button.setShortcut("Return")
        self.log_in_connect_button.clicked.connect(self._log_in)
        self.sign_up_button.clicked.connect(self._sign_up)
        qr = self.sign_up.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        self.sign_up.move(qr.topLeft())

        self.sign_up_layout.addWidget(self.sign_up_button, 4, 0)
        self.sign_up_layout.addWidget(self.log_in_connect_button, 4, 1)
        self.sign_up_layout.addWidget(self.username, 1, 0, 1, 2)
        self.sign_up_layout.addWidget(self.password_retype, 3, 0, 1, 2)
        self.sign_up_layout.addWidget(self.password, 2, 0, 1, 2)
        self.username.setDisabled(False)
        self.password.setDisabled(False)
        self.password_retype.setDisabled(False)
        self.sign_up.setLayout(self.sign_up_layout)
        self.sign_up.show()
        self.username.setFocusPolicy(Qt.StrongFocus)
        self.username.setFocus()
        return

    def _log_in(self):
        self.sign_up.close()
        return self.connect()

    def load_palette(self):
        """Set dark style theme"""
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.WindowText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Base, QColor(25, 25, 25))
        dark_palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.ToolTipText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Text, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ButtonText, QColor(255, 255, 255))
        dark_palette.setColor(QPalette.BrightText, QColor(255, 0, 0))
        dark_palette.setColor(QPalette.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.HighlightedText, QColor(0, 0, 0))

        self.app.setStyle('Fusion')
        self.app.setPalette(dark_palette)
        return


if __name__ == '__main__':
    appctxt = PentaTournament()
    exit_code = appctxt.app.exec_()      # 2. Invoke appctxt.app.exec_()
    sys.exit(exit_code)
