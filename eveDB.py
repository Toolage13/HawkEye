# !/usr/local/bin/python3.8
# Github: https://github.com/Toolage13/HawkEye
"""
This is the EveDB class, which handles most of the management of the local files and database.
"""
from aiohttp import ClientSession
import config
import csv
import datetime
import logging
import json
from math import sqrt
import os
import requests
import statusmsg
import sqlite3
import time

Logger = logging.getLogger(__name__)


class EveDB:
    def __init__(self):
        fuzzwork_download()
        Logger.info('Creating eveDB object...')
        self.__connection = None
        self.__cursor = None
        self._blops = None
        self._capital_ships = None
        self._gate_positions = {}
        self._higgs = None
        self.__local_db = None
        self.__local_c = None
        self._map_regions = {}
        self._map_solar_systems = {}
        self._mtu = None
        self._nano_bullshit = None
        self._recon_ships = None
        self._region_map = None
        self._rookie_ships = None
        self._seals = None
        self._smartbomb_ids = None
        self._super = None
        self._titan = None
        self.__load_tables()
        self.__prepare_local_db()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__connection.close()
        self.__local_db.close()

    def __load_tables(self):
        db_exists = os.path.exists(os.path.join(config.PREF_PATH, 'staticdata.db'))
        self.__connection = sqlite3.connect(os.path.join(config.PREF_PATH, "staticdata.db"), check_same_thread=False)
        self.__cursor = self.__connection.cursor()
        if not db_exists:
            with open(os.path.join(config.PREF_PATH, 'invTypes.csv'), encoding='utf8') as file:
                rows = csv.reader(file)
                self.__cursor.execute("""create table if not exists invTypes(
                        typeID int,
                        groupID int,
                        typeName str,
                        description str,
                        mass int,
                        volume int,
                        capacity int,
                        portionSize int,
                        raceID int,
                        basePrice int,
                        published int,
                        marketGroupID int,
                        iconID int,
                        soundID int,
                        graphicID int)
                        """)
                self.__cursor.executemany("insert into invTypes values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                          rows)

            with open(os.path.join(config.PREF_PATH, 'invGroups.csv'), encoding='utf8') as file:
                rows = csv.reader(file)
                self.__cursor.execute("""create table if not exists invGroups(
                                   groupID int,
                                   categoryID int,
                                   groupName str,
                                   iconID str,
                                   useBasePrice int,
                                   anchored int,
                                   anchorable int,
                                   fittableNonSingleton int,
                                   published int)
                                """)
                self.__cursor.executemany("insert into invGroups values (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

            with open(os.path.join(config.PREF_PATH, 'mapSolarSystems.csv'), encoding='utf8') as file:
                rows = csv.reader(file)
                self.__cursor.execute("""create table if not exists mapSolarSystems(
                                   regionID int,
                                   constellationID int,
                                   solarSystemID int,
                                   solarSystemName str,
                                   x int,
                                   y int,
                                   z int,
                                   xMin int,
                                   xMax int,
                                   yMin int,
                                   yMax int,
                                   zMin int,
                                   zMax int,
                                   luminosity float,
                                   border int,
                                   fringe int,
                                   corridor int,
                                   hub int,
                                   international int,
                                   regional int,
                                   constellation str,
                                   security float,
                                   factionID int,
                                   radius int,
                                   sunTypeID int,
                                   securityClass str)
                                """)
                self.__cursor.executemany("insert into mapSolarSystems values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                                          "?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

            with open(os.path.join(config.PREF_PATH, 'mapRegions.csv'), encoding='utf8') as file:
                rows = csv.reader(file)
                self.__cursor.execute("""create table if not exists mapRegions(
                                    regionID int,
                                    regionName str,
                                    x int,
                                    y int,
                                    z int,
                                    xMin int,
                                    xMax int,
                                    yMin int,
                                    yMax int,
                                    zMin int,
                                    zMax int,
                                    factionID int,
                                    radius int)
                                    """)
                self.__cursor.executemany("insert into mapRegions values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                          rows)

            with open(os.path.join(config.PREF_PATH, 'mapDenormalize.csv'), encoding='utf8') as file:
                rows = csv.reader(file)
                self.__cursor.execute("""create table if not exists mapDenormalize(
                        itemID int,
                        typeID int,
                        groupID int,
                        solarSystemID int,
                        constellationID int,
                        regionID int,
                        orbitID str,
                        x float,
                        y float,
                        z float,
                        radius str,
                        itemName str,
                        security float,
                        celestialIndex str,
                        orbitIndex str)
                        """)
                self.__cursor.executemany("insert into mapDenormalize values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, "
                                          "?, ?)", rows)

        self.__connection.commit()

        self.__cursor.execute("""select regionID, regionName from mapRegions""")
        for tup in self.__cursor.fetchall():
            self._map_regions[tup[0]] = tup[1]

        self.__cursor.execute("""select solarSystemID, regionID, security from mapSolarSystems""")
        for tup in self.__cursor.fetchall():
            self._map_solar_systems[tup[0]] = {'regionID': tup[1], 'security': tup[2]}

        self.__cursor.execute("""select solarSystemID, x, y, z from mapDenormalize where groupID = 10""")
        for tup in self.__cursor.fetchall():
            if tup[0] in self._gate_positions.keys():
                self._gate_positions[tup[0]].append({'x': tup[1], 'y': tup[2], 'z': tup[3]})
            else:
                self._gate_positions[tup[0]] = [{'x': tup[1], 'y': tup[2], 'z': tup[3]}]

        self.__cursor.execute("select typeID from invTypes where groupID = 72")
        self._smartbomb_ids = [row[0] for row in self.__cursor.fetchall()]

        self.__cursor.execute("""select typeID from invTypes where typeName in (
                            'Garmur',
                            'Orthrus',
                            'Barghest',
                            'Succubus',
                            'Phantasm',
                            'Nightmare',
                            'Keres',
                            'Hyena',
                            'Retribution',
                            'Omen Navy Issue',
                            'Osprey Navy Issue',
                            'Kikimora')""")

        self._nano_bullshit = [row[0] for row in self.__cursor.fetchall()]

        self.__cursor.execute("select typeID from invTypes where groupID in (485, 547, 1538, 883, 1013, 30)")
        self.capital_ships = [row[0] for row in self.__cursor.fetchall()]

        self.__cursor.execute("select typeID from invTypes where groupID = 237")
        self.rookie_ships = [row[0] for row in self.__cursor.fetchall()]

        self.__cursor.execute("select typeID from invTypes where groupID = 833")
        self.recon_ships = [row[0] for row in self.__cursor.fetchall()]

        self.__cursor.execute("select typeID from invTypes where groupID in (1250, 1246)")
        self.mtu = [row[0] for row in self.__cursor.fetchall()]

        self.__cursor.execute("select typeID from invTypes where groupID = 898")
        self.blops = [row[0] for row in self.__cursor.fetchall()]

        self.__cursor.execute("select typeID from invTypes where groupID in (28, 463, 543, 941, 513, 380, 1202)")
        self.seals = [row[0] for row in self.__cursor.fetchall()]

        self.__cursor.execute("select typeID from invTypes where groupID = 1308")
        self.higgs = [row[0] for row in self.__cursor.fetchall()]

        self.__cursor.execute("select typeID from invTypes where groupID = 659")
        self.super = [row[0] for row in self.__cursor.fetchall()]

        self.__cursor.execute("select typeID from invTypes where groupID = 30")
        self.titan = [row[0] for row in self.__cursor.fetchall()]

        return None

    def __prepare_local_db(self):
        self.__local_db = sqlite3.connect(os.path.join(config.PREF_PATH, 'characters.db'),
                                          check_same_thread=False,
                                          detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
                                          )
        self.__local_c = self.__local_db.cursor()

        self.__local_c.execute("""create table if not exists characters(
                                char_id int,
                                char_name str,
                                corp_id int,
                                corp_name str,
                                alliance_id int,
                                alliance_name str,
                                last_update timestamp)""")
        self.__local_c.execute("""create table if not exists entities(
                                entity_id int,
                                entity_name str,
                                last_update timestamp)""")

    def get_region(self, region_id):
        return self._map_regions[self._map_solar_systems[region_id]['regionID']]

    def get_location(self, i):
        """
        :param i: solar_system_id
        :return: Location dictionary key
        """

        sec_status = self._map_solar_systems[i]['security']

        if sec_status > 0.499999:
            return 'highsec'
        if sec_status > 0.01:
            return 'lowsec'
        if sec_status == -0.99:
            return 'wormhole'
        return 'nullsec'

    async def get_pilot_id(self, pilot_name):
        self.__local_c.execute("select char_id, last_update from characters where char_name = ?", (pilot_name, ))
        r = self.__local_c.fetchone()
        if r is not None:
            if datetime.datetime.now() > (r[1] + datetime.timedelta(days=7)):
                self.__local_c.execute("delete from characters where char_name = ?", (pilot_name, ))
            else:
                return {'pilot_id': r[0], 'pilot_name': pilot_name}

        url = 'https://esi.evetech.net/latest/search/?categories=character&strict=true&search="{}"'.format(
            pilot_name.replace(' ', '%20'))
        headers = {'User-Agent': 'HawkEye, Author: Kain Tarr'}
        start_time = time.time()
        async with ClientSession() as session:
            while True:
                async with session.get(url, headers=headers) as resp:
                    try:
                        r = await resp.json()
                        break
                    except Exception as e:
                        Logger.warning(resp)
                        Logger.warning(e)
                        time.sleep(0.25)
        Logger.info('Requested {} and got it in {} seconds'.format(url, round(time.time() - start_time, 2)))
        try:
            sql = "insert into characters (char_id, char_name, last_update) values (?, ?, ?)"
            self.__local_c.execute(sql, (r['character'][0], pilot_name, datetime.datetime.now()))
            self.__local_db.commit()
            return {'pilot_id': r['character'][0], 'pilot_name': pilot_name}
        except KeyError:
            return None

    def get_pilot_affiliations(self, pilot_map):
        for pilot in pilot_map:
            for key in ['corp_id', 'corp_name', 'alliance_id', 'alliance_name']:
                pilot[key] = None
        cols = ['char_id', 'corp_id', 'alliance_id']
        # Update pilot_map with corp_id and alliance_id from database
        self.__local_c.execute("select {} from characters where char_id in ({})".format(', '.join(cols), ', '.join(
            ['?'] * len(pilot_map))), [p['pilot_id'] for p in pilot_map])
        results = self.__local_c.fetchall()
        for pilot in pilot_map:
            for r in results:
                if pilot['pilot_id'] == r[0]:
                    pilot['corp_id'] = r[1]
                    pilot['alliance_id'] = r[2]

        # If none of our pilots is missing corp_id, they were all up-to-date in the database, and we can return results
        # after adding corporation names and alliance names from _add_corpall_names
        if None not in [r['corp_id'] for r in pilot_map]:
            return self.__add_corpall_names(pilot_map)

        # Determine which characters were not up-to-date in the database by checking where corp_id is missing
        pilots_not_in_db = [p for p in pilot_map if p.get('corp_id') is None]
        # Reset our pilot_map to exclude characters with missing corp_id
        pilot_map = [p for p in pilot_map if p.get('corp_id') is not None]

        while True:
            try:
                affiliations = post_req_ccp("characters/affiliation/", json.dumps(
                    tuple(p['pilot_id'] for p in pilots_not_in_db)))
                break
            except Exception as e:
                Logger.warning(e)
                time.sleep(0.25)

        for pilot in pilots_not_in_db:
            for mapping in affiliations:
                if pilot['pilot_id'] == mapping['character_id']:
                    # Enrich pilot with corp_id and alliance_id from CCP for pilots not in database
                    pilot['corp_id'] = mapping['corporation_id']
                    pilot['alliance_id'] = mapping.get('alliance_id')
                    # Insert pilot data into characters
                    sql = "insert into characters ({}, last_update) values (?, ?, ?, ?)".format(', '.join(cols))
                    self.__local_c.execute(sql, (mapping['character_id'],
                                                 mapping['corporation_id'],
                                                 mapping.get('alliance_id'),
                                                 datetime.datetime.now()))
                    self.__local_db.commit()
            # Pilot data is enriched with corp_id and alliance_id, add it back to pilot_map
            pilot_map.append(pilot)
        return self.__add_corpall_names(pilot_map)

    def __add_corpall_names(self, pilot_map):
        corpall_ids = []
        for pilot in pilot_map:
            for key in ['corp_id', 'alliance_id']:
                if pilot[key] is not None:
                    corpall_ids.append(pilot[key])
        affiliation_names = self.__get_affil_names(corpall_ids)

        # Add corp and alliance names to affiliations using _get_affil_names mapping results
        for pilot in pilot_map:
            for d in affiliation_names:
                if pilot['corp_id'] == d['id']:
                    pilot['corp_name'] = d['name']
                if pilot['alliance_id'] == d['id']:
                    pilot['alliance_name'] = d['name']

        return pilot_map

    def __get_affil_names(self, allcorp_ids):
        allcorp_ids = [i for i in allcorp_ids if i]
        return_values = []
        self.__local_c.execute("select entity_id, entity_name, last_update from entities where entity_id in ({})".format(
            ','.join(['?'] * len(allcorp_ids))), allcorp_ids)
        records = self.__local_c.fetchall()
        if records is not None:
            for r in records:
                return_values.append({'id': r[0], 'name': r[1]})
            allcorp_ids = list(set(allcorp_ids).difference([d['id'] for d in return_values]))
            if len(allcorp_ids) == 0:
                return return_values

        while True:
            try:
                names = post_req_ccp("universe/names/", json.dumps(tuple(allcorp_ids)))
                break
            except Exception as e:
                Logger.warning(e)
                time.sleep(0.25)

        for r in names:
            return_values.append({'id': r['id'], 'name': r['name']})
            sql = "insert into entities (entity_id, entity_name, last_update) values (?, ?, ?)"
            self.__local_c.execute(sql, (r['id'], r['name'], datetime.datetime.now()))
            self.__local_db.commit()
        return return_values

    def get_ship_name(self, i):
        if i in [None, '']:
            return None
        self.__cursor.execute("""select typeName from invTypes where typeID = {}""".format(i))
        return self.__cursor.fetchone()[0]

    def is_capital(self, i):
        """
        :param i: ship_type_id
        :return: Boolean
        """

        if i in self.capital_ships:
            return True
        return False

    def is_nano(self, i):
        """
        :param i: ship_type_id
        :return: Boolean
        """

        if i in self._nano_bullshit:
            return True
        return False

    def is_recon(self, i):
        """
        :param : ship_type_id
        :return: Boolean
        """

        if i in self.recon_ships:
            return True
        return False

    def is_super(self, i):
        """
        :param i: ship_type_id
        :return: Boolean
        """

        if i in self.super:
            return True
        return False

    def is_titan(self, i):
        """
        :param i: ship_type_id
        :return: Boolean
        """

        if i in self.titan:
            return True
        return False

    def killed_on_gate(self, killmail):
        pos = self._get_gate_positions(killmail['solar_system_id'])
        if pos is None or killmail['victim'].get('position') is None:
            return False
        for position in pos:
            if self._get_position_distance(killmail['victim']['position'], position) < 40:
                return True
        return False

    def _get_gate_positions(self, i):
        return self._gate_positions.get(i)

    @staticmethod
    def _get_position_distance(a, b):
        return sqrt((a['x'] - b['x']) ** 2 + (a['y'] - b['y']) ** 2 + (a['z'] - b['z']) ** 2) / 1000

    def used_blops(self, a, p):
        """
        :param a: dictionary of attackers
        :param p: pilot id
        :return: Boolean
        """

        for d in a:
            if d.get('character_id') == p and d.get('ship_type_id') in self.blops:
                return True
        return False

    def used_capital(self, a, p):
        """
        :param a: Dictionary of attackers
        :param p: pilot id
        :return: Boolean
        """

        for d in a:
            if d.get('character_id') == p and self.is_capital(d.get('ship_type_id')):
                return True
        return False

    def used_cyno(self, a, p):
        """
        :param a: Dictionary of attackers
        :param p: pilot id
        :return: Boolean
        """

        for d in a:
            if d.get('character_id') == p and self.is_recon(d.get('ship_type_id')):
                return True
        return False

    def used_nano(self, a, p):
        """
        :param a: Dictionary of attackers
        :param p: pilot id
        :return: Boolean
        """

        for d in a:
            if d.get('character_id') == p and self.is_nano(d.get('ship_type_id')):
                return True
        return False

    def used_smartbomb(self, a, p):
        """
        :param a: dictionary of attackers
        :param p: pilot id
        :return: Boolean
        """

        for d in a:
            if d.get('character_id') == p and d.get('weapon_type_id') in self._smartbomb_ids:
                return True
        return False

    def used_super(self, a, p):
        """
        :param a: Dictionary of attackers
        :param p: pilot id
        :return: Boolean
        """

        for d in a:
            if d.get('character_id') == p and self.is_super(d.get('ship_type_id')):
                return True
        return False

    def used_titan(self, a, p):
        """
        :param a: Dictionary of attackers
        :param p: pilot id
        :return: Boolean
        """

        for d in a:
            if d.get('character_id') == p and self.is_titan(d.get('ship_type_id')):
                return True
        return False


def clear_characters():
    db = sqlite3.connect(os.path.join(config.PREF_PATH, 'characters.db'),
                         check_same_thread=False,
                         detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
                         )
    c = db.cursor()
    c.execute("""delete from characters""")
    c.execute("""delete from entities""")
    c.execute("""create table if not exists characters(
                                    char_id int,
                                    char_name str,
                                    corp_id int,
                                    corp_name str,
                                    alliance_id int,
                                    alliance_name str,
                                    last_update timestamp)""")
    c.execute("""create table if not exists entities(
                                    entity_id int,
                                    entity_name str,
                                    last_update timestamp)""")
    db.commit()
    db.close()


def fuzzwork_download():
    for file in ['invTypes.csv', 'invGroups.csv', 'mapSolarSystems.csv', 'mapRegions.csv', 'mapDenormalize.csv']:
        if not os.path.exists(os.path.join(config.PREF_PATH, file)):
            get_file(file)


def get_file(file):
    Logger.info('Need to download file {}'.format("https://www.fuzzwork.co.uk/dump/latest/{}".format(file)))
    statusmsg.push_status('Need to download file {}'.format("https://www.fuzzwork.co.uk/dump/latest/{}".format(file
                                                                                                               )))
    url = "https://www.fuzzwork.co.uk/dump/latest/{}".format(file)
    headers = {'Accept-Encoding': 'gzip', 'User-Agent': 'HawkEye, Author: Kain Tarr'}
    resp = requests.get(url, headers=headers)
    open(os.path.join(config.PREF_PATH, file), 'wb').write(resp.content)


def post_req_ccp(esi_path, json_data):
    url = "https://esi.evetech.net/latest/" + esi_path + "?datasource=tranquility"
    try:
        start_time = time.time()
        headers = {'User-Agent': 'HawkEye, Author: Kain Tarr'}
        r = requests.post(url, json_data, headers=headers)
        Logger.info('Requested {} and got it in {} seconds'.format(url, round(time.time() - start_time, 3)))
    except requests.exceptions.ConnectionError:
        Logger.info("No network connection.", exc_info=True)
        statusmsg.push_status("NETWORK ERROR: Check your internet connection and firewall settings.")
        time.sleep(5)
        return "network_error"
    if r.status_code != 200:
        try:
            statusmsg.push_status(json.loads(r.text)["error"])
            Logger.warning(json.loads(r.text)["error"])
        except json.decoder.JSONDecodeError:
            Logger.error('Failed to return {}'.format(url))
        Logger.info("CCP Servers at (" + esi_path + ") returned error code: " + str(r.status_code) + ", saying: ",
                    exc_info=True)
        statusmsg.push_status("CCP SERVER ERROR: " + str(r.status_code))
        return "server_error"
    return r.json()
