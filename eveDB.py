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


class eveDB:
    def __init__(self):
        self.db_queue = []

        for file in ['invTypes.csv', 'invGroups.csv', 'mapSolarSystems.csv', 'mapRegions.csv', 'mapDenormalize.csv']:
            if not os.path.exists(os.path.join(config.PREF_PATH, file)):
                self.get_file(file)

        Logger.info('Creating eveDB object...')
        self.connection = sqlite3.connect(":memory:", check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.blops = None
        self.capital_ships = None
        self.gate_positions = {}
        self.higgs = None
        self.map_regions = {}
        self.map_solar_systems = {}
        self.mtu = None
        self.nano_bullshit = None
        self.recon_ships = None
        self.region_map = None
        self.rookie_ships = None
        self.seals = None
        self.smartbomb_ids = None
        self.super = None
        self.titan = None
        self.load_tables()

        self.local_db = sqlite3.connect(os.path.join(config.PREF_PATH, 'characters.db'),
                                        check_same_thread=False,
                                        detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES)
        self.local_c = self.local_db.cursor()
        self.prepare_local_db()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.connection.close()
        self.local_db.close()
        self.local_km.close()

    def load_tables(self):
        with open(os.path.join(config.PREF_PATH, 'invTypes.csv'), encoding='utf8') as file:
            rows = csv.reader(file)
            try:
                self.cursor.execute("""create table invTypes(
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
            except:
                pass
            self.cursor.executemany("insert into invTypes values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

        with open(os.path.join(config.PREF_PATH, 'invGroups.csv'), encoding='utf8') as file:
            rows = csv.reader(file)
            try:
                self.cursor.execute("""create table invGroups(
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
            except:
                pass
            self.cursor.executemany("insert into invGroups values (?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

        with open(os.path.join(config.PREF_PATH, 'mapSolarSystems.csv'), encoding='utf8') as file:
            rows = csv.reader(file)
            try:
                self.cursor.execute("""create table mapSolarSystems(
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
            except:
                pass
            self.cursor.executemany(
                "insert into mapSolarSystems values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

        self.cursor.execute("""select solarSystemID, regionID, security from mapSolarSystems""")
        for tup in self.cursor.fetchall():
            self.map_solar_systems[tup[0]] = {'regionID': tup[1], 'security': tup[2]}

        with open(os.path.join(config.PREF_PATH, 'mapRegions.csv'), encoding='utf8') as file:
            rows = csv.reader(file)
            try:
                self.cursor.execute("""create table mapRegions(
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
            except:
                pass
            self.cursor.executemany(
                "insert into mapRegions values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows)

        self.cursor.execute("""select regionID, regionName from mapRegions""")
        for tup in self.cursor.fetchall():
            self.map_regions[tup[0]] = tup[1]

        with open(os.path.join(config.PREF_PATH, 'mapDenormalize.csv'), encoding='utf8') as file:
            rows = csv.reader(file)
            try:
                self.cursor.execute("""create table mapDenormalize(
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
            except:
                pass
            self.cursor.executemany("insert into mapDenormalize values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows)

        self.cursor.execute("""select solarSystemID, x, y, z from mapDenormalize where groupID = 10""")
        for tup in self.cursor.fetchall():
            if tup[0] in self.gate_positions.keys():
                self.gate_positions[tup[0]].append({'x': tup[1], 'y': tup[2], 'z': tup[3]})
            else:
                self.gate_positions[tup[0]] = [{'x': tup[1], 'y': tup[2], 'z': tup[3]}]

        self.cursor.execute("select typeID from invTypes where groupID = 72")
        self.smartbomb_ids = [row[0] for row in self.cursor.fetchall()]

        self.cursor.execute("""select typeID from invTypes where typeName in (
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
        self.nano_bullshit = [row[0] for row in self.cursor.fetchall()]

        self.cursor.execute("select typeID from invTypes where groupID in (485, 547, 1538, 883, 1013, 30)")
        self.capital_ships = [row[0] for row in self.cursor.fetchall()]

        self.cursor.execute("select typeID from invTypes where groupID = 237")
        self.rookie_ships = [row[0] for row in self.cursor.fetchall()]

        self.cursor.execute("select typeID from invTypes where groupID = 833")
        self.recon_ships = [row[0] for row in self.cursor.fetchall()]

        self.cursor.execute("select typeID from invTypes where groupID in (1250, 1246)")
        self.mtu = [row[0] for row in self.cursor.fetchall()]

        self.cursor.execute("select typeID from invTypes where groupID = 898")
        self.blops = [row[0] for row in self.cursor.fetchall()]

        self.cursor.execute("select typeID from invTypes where groupID in (28, 463, 543, 941, 513, 380, 1202)")
        self.seals = [row[0] for row in self.cursor.fetchall()]

        self.cursor.execute("select typeID from invTypes where groupID = 1308")
        self.higgs = [row[0] for row in self.cursor.fetchall()]

        self.cursor.execute("select typeID from invTypes where groupID = 659")
        self.super = [row[0] for row in self.cursor.fetchall()]

        self.cursor.execute("select typeID from invTypes where groupID = 30")
        self.titan = [row[0] for row in self.cursor.fetchall()]

        return None

    def prepare_local_db(self):
        self.local_c.execute("""create table if not exists characters(
                                char_id int,
                                char_name str,
                                corp_id int,
                                corp_name str,
                                alliance_id int,
                                alliance_name str,
                                last_update timestamp)""")
        self.local_c.execute("""create table if not exists allcorp(
                                entity_id int,
                                entity_name str,
                                last_update timestamp)""")

    async def prepare_local_km(self):
        self.local_km = await aiosqlite.connect(os.path.join(config.PREF_PATH, 'killmails.db'))
        self.local_ckm = await self.local_km.cursor()
        await self.local_km.execute("""create table if not exists killmails(
                                        killmail_id int,
                                        killmail_time str,
                                        solar_system_id int)""")

        await self.local_km.execute("""create table if not exists victims(
                                        killmail_id int,
                                        alliance_id int,
                                        character_id int,
                                        corporation_id int,
                                        damage_taken int,
                                        ship_type_id int)""")

        await self.local_km.execute("""create table if not exists items(
                                        killmail_id int,
                                        flag int,
                                        item_type_id int,
                                        quantity_destroyed int,
                                        quantity_dropped int,
                                        singleton int)""")

        await self.local_km.execute("""create table if not exists position(
                                        killmail_id int,
                                        x real,
                                        y real,
                                        z real)""")

        await self.local_km.execute("""create table if not exists attackers(
                                        killmail_id int,
                                        alliance_id int,
                                        character_id int,
                                        corporation_id int,
                                        damage_done int,
                                        final_blow boolean,
                                        security_status real,
                                        ship_type int,
                                        weapon_type_id int)""")

    def get_region(self, region_id):
        return self.map_regions[self.map_solar_systems[region_id]['regionID']]

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

    def is_super(self, id):
        """
        :param id: ship_type_id
        :return: Boolean
        """

        if id in self.super:
            return True
        return False

    def is_titan(self, id):
        """
        :param id: ship_type_id
        :return: Boolean
        """

        if id in self.titan:
            return True
        return False

    def is_recon(self, id):
        """
        :param id: ship_type_id
        :return: Boolean
        """

        if id in self.recon_ships:
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

    def is_capital(self, id):
        """
        :param id: ship_type_id
        :return: Boolean
        """

        if id in self.capital_ships:
            return True
        return False

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

    def is_nano(self, id):
        """
        :param id: ship_type_id
        :return: Boolean
        """

        if id in self.nano_bullshit:
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

    def get_ship_name(self, id):
        try:
            self.cursor.execute("""select typeName from invTypes where typeID = {} """.format(id))
        except:
            Logger.debug('Failed to run {} through get_ship_name()'.format(id))
            return 'UNKNOWN'
        return self.cursor.fetchone()[0]

    def get_location(self, id):
        """
        :param id: solar_system_id
        :return: Location dictionary key
        """

        sec_status = self.map_solar_systems[id]['security']

        if sec_status > 0.499999:
            return 'trash_can_resident'
        if sec_status > 0.01:
            return 'countryside_hillbilly'
        if sec_status == -0.99:
            return 'vietcong'
        return 'coastal_city_elite'

    def used_smartbomb(self, a, p):
        """
        :param c: sqlite3 cursor
        :param a: dictionary of attackers
        :param p: pilot id
        :return: Boolean
        """

        for d in a:
            if d.get('character_id') == p and d.get('weapon_type_id') in self.smartbomb_ids:
                return True
        return False

    def killed_on_gate(self, killmail):
        pos = self.get_gate_positions(killmail['solar_system_id'])
        if pos is None or killmail['victim'].get('position') is None:
            return False
        for position in pos:
            if self.get_position_distance(killmail['victim']['position'], position) < 40:
                return True
        return False

    def get_gate_positions(self, id):
        return self.gate_positions.get(id)

    def get_position_distance(self, a, b):
        return sqrt((a['x'] - b['x']) ** 2 + (a['y'] - b['y']) ** 2 + (a['z'] - b['z']) ** 2) / 1000

    def get_file(self, file):
        Logger.info('Need to download file {}'.format("https://www.fuzzwork.co.uk/dump/latest/{}".format(file)))
        statusmsg.push_status('Need to download file {}'.format("https://www.fuzzwork.co.uk/dump/latest/{}".format(file)))
        url = "https://www.fuzzwork.co.uk/dump/latest/{}".format(file)
        headers = {'Accept-Encoding': 'gzip', 'User-Agent': 'HawkEye, Author: Kain Tarr'}
        resp = requests.get(url, headers=headers)
        open(os.path.join(config.PREF_PATH, file), 'wb').write(resp.content)

    async def get_pilot_id(self, name):
        try:
            self.local_c.execute("""select char_id, last_update from characters where char_name = "{}" """.format(name))
            r = self.local_c.fetchone()
        except:
            Logger.warning('get_pilot_id({}) failed first query.'.format(name))
            r = None
        if r is not None:
            Logger.debug('get_pilot_id({}) returned {}.'.format(name, r))
            if datetime.datetime.now() > (r[1] + datetime.timedelta(days=7)):
                self.local_c.execute("""delete from characters where char_name = ?""", name)
            else:
                return r[0]

        url = 'https://esi.evetech.net/latest/search/?categories=character&strict=true&search="{}"'.format(name.replace(' ', '%20'))
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
        Logger.info('Requested {} and got it in {} seconds'.format(url, round(time.time() - start_time, 3)))
        try:
            sql = """insert into characters (char_id, char_name, last_update) values (?, ?, ?)"""
            self.local_c.execute(sql, (r['character'][0], name, datetime.datetime.now()))
            self.local_db.commit()
            return r['character'][0]
        except KeyError:
            return None

    def get_char_affiliations(self, char_ids):
        self.local_c.execute("""select char_id, corp_id, alliance_id, last_update from characters where char_id in ({})""".format(','.join(['?'] * len(char_ids))), char_ids)
        r = self.local_c.fetchall()
        results = [{'character_id': d[0], 'corporation_id': d[1], 'alliance_id': d[2]} for d in r]
        if len(results) == len(char_ids):
            if None not in [d['corporation_id'] for d in results]:
                return results

        statusmsg.push_status("Retrieving character affiliation IDs...")
        try:
            affiliations = post_req_ccp("characters/affiliation/", json.dumps(tuple(char_ids)))
            for mapping in affiliations:
                sql = "update characters set corp_id = ?, alliance_id = ?, last_update = ? where char_id = ?"
                self.local_c.execute(sql, (mapping['corporation_id'],
                                           mapping.get('alliance_id'),
                                           datetime.datetime.now(),
                                           mapping['character_id']))
                self.local_db.commit()
        except:
            Logger.info("Failed to obtain character affiliations.", exc_info=True)
            raise Exception

        return affiliations

    def get_affil_names(self, allcorp_ids):
        allcorp_ids = [i for i in allcorp_ids if i]
        return_values = []
        self.local_c.execute("""select entity_id, entity_name, last_update from allcorp where entity_id in ({})""".format(','.join(['?'] * len(allcorp_ids))), allcorp_ids)
        records = self.local_c.fetchall()
        if records is not None:
            Logger.debug('get_affil_names({}) returned {}.'.format(allcorp_ids, records))
            for r in records:
                if datetime.datetime.now() > (r[2] + datetime.timedelta(days=7)):
                    self.local_c.execute("""delete from allcorp where entity_id = {}""".format(r[0]))
                else:
                    return_values.append({'id': r[0], 'name': r[1]})
            allcorp_ids = list(set(allcorp_ids).difference([d['id'] for d in return_values]))
            if len(allcorp_ids) == 0:
                return return_values

        statusmsg.push_status("Obtaining corporation and alliance names and zKillboard data...")
        try:
            names = post_req_ccp("universe/names/", json.dumps(tuple(allcorp_ids)))
        except:
            Logger.info("Failed request corporation and alliance names.", exc_info=True)
            raise Exception

        records = []
        for r in names:
            records.append({'id': r['id'], 'name': r['name']})
            sql = """insert into allcorp (entity_id, entity_name, last_update) values (?, ?, ?)"""
            self.local_c.execute(sql, (r['id'], r['name'], datetime.datetime.now()))
            self.local_db.commit()
        return records

    async def get_char_name(self, id):
        if id == '':
            return ''
        if id == None:
            return ''
        Logger.debug('Running get_char_name for id: {}'.format(id))
        self.local_c.execute("""select char_name, last_update from characters where char_id = {}""".format(id))
        r = self.local_c.fetchone()
        if r is not None:
            if datetime.datetime.now() > (r[1] + datetime.timedelta(days=7)):
                self.local_c.execute("""delete from characters where char_id = {}""".format(id))
            else:
                return r[0]

        url = 'https://esi.evetech.net/latest/characters/{}?datasource=tranquility'.format(id)
        headers = {'User-Agent': 'SpyStats, Author: Kain Tarr'}
        start_time = time.time()
        # resp = await requests.get(url, headers=headers)
        async with ClientSession() as session:
            async with session.get(url) as resp:
                r = await resp.json()
        Logger.info('Requested {} and got it in {} seconds'.format(url, round(time.time() - start_time, 3)))
        try:
            sql = """insert into characters (char_id, char_name, last_update) values (?, ?, ?)"""
            self.local_c.execute(sql, (id, r['name'], datetime.datetime.now()))
            self.local_db.commit()
            return r['name']
        except:
            print('Failed to get name for character id {} using get_char_name()'.format(id))
            return 'N/A'

    def query_characters(self, char_names):
        self.local_c.execute("""select char_id, char_name, corp_id, alliance_id from characters where char_name in ({})""".format(','.join(['?'] * len(char_names))), char_names)
        return [{'char_id': r[0], 'char_name': r[1], 'corp_id': r[2], 'alliance_id': r[3]} for r in self.local_c.fetchall()]

    def queue_killmail(self, json_data):
        self.db_queue.append(json_data)

    async def process_queue(self):
        l = len(self.db_queue)
        for j in self.db_queue:
            await self.store_killmail(j)
        self.db_queue = []
        return l

    async def insert_sql(self, table, columns, values):
        sql = """insert into {} (killmail_id, {}) values ({})""".format(table, ', '.join(columns), ','.join('?'*len(values)))
        await self.local_km.execute(sql, tuple(values))
        await self.local_km.commit()

    async def store_killmail(self, json_data):
        k = tuple([json_data['killmail_id']])
        m = ['killmail_time', 'solar_system_id']
        t = k + tuple([json_data[i] for i in m])
        await self.insert_sql('killmails', m, t)

        m = ['alliance_id', 'character_id', 'corporation_id', 'damage_taken', 'ship_type_id']
        t = k + tuple([json_data['victim'].get(i) for i in m])
        await self.insert_sql('victims', m, t)

        m = ['flag', 'item_type_id', 'quantity_destroyed', 'quantity_dropped', 'singleton']
        for i in json_data['victim']['items']:
            t = k + tuple([i.get(x) for x in m])
            await self.insert_sql('items', m, t)

        m = ['x', 'y', 'z']
        t = k + tuple([json_data['victim']['position'].get(i) for i in m])
        await self.insert_sql('position', m, t)

        m = ['alliance_id', 'character_id', 'corporation_id', 'damage_done', 'final_blow', 'security_status', 'ship_type', 'weapon_type_id']
        for i in json_data['attackers']:
            t = k + tuple([i.get(x) for x in m])
            await self.insert_sql('attackers', m, t)

    async def get_killmail(self, killmail_id):
        d = {}
        await self.local_km.execute("select killmail_time, solar_system_id from killmails where killmail_id = ?", (killmail_id, ))
        r = await self.local_ckm.fetchone()
        if not r:
            return None
        d['killmail_id'] = killmail_id
        d['killmail_time'] = r[0]
        d['solar_system_id'] = r[1]

        m = ['alliance_id', 'character_id', 'corporation_id', 'damage_taken', 'ship_type_id']
        await self.local_km.execute("select {} from victims where killmail_id = ?".format(', '.join(m)), (killmail_id, ))
        r = await self.local_ckm.fetchone()
        victim = {}
        for i in m:
            victim[i] = r[m.index(i)]
        d['victim'] = victim

        m = ['flag', 'item_type_id', 'quantity_destroyed', 'quantity_dropped', 'singleton']
        await self.local_km.execute("select {} from items where killmail_id = ?".format(', '.join(m)), (killmail_id, ))
        r = await self.local_ckm.fetchall()
        items = []
        for item in r:
            new_dict = {}
            for col in m:
                new_dict[col] = item[m.index(col)]
            items.append(new_dict)
        d['victim']['items'] = items

        m = ['x', 'y', 'z']
        await self.local_km.execute("select {} from position where killmail_id = ?".format(', '.join(m)), (killmail_id, ))
        r = await self.local_ckm.fetchone()
        position = {}
        for i in m:
            position[i] = r[m.index(i)]
        d['victim']['position'] = position

        m = ['alliance_id', 'character_id', 'corporation_id', 'damage_done', 'final_blow', 'security_status', 'ship_type', 'weapon_type_id']
        await self.local_km.execute("select {} from attackers where killmail_id = ?".format(', '.join(m)), (killmail_id, ))
        r = await self.local_ckm.fetchall()
        attackers = []
        for att in r:
            new_dict = {}
            for col in m:
                new_dict[col] = att[m.index(col)]
            attackers.append(new_dict)
        d['attackers'] = attackers

        return d


def clear_characters():
    db = sqlite3.connect(os.path.join(config.PREF_PATH, 'characters.db'),
                         check_same_thread=False,
                         detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
                         )
    c = db.cursor()
    c.execute("""delete from characters""")
    db.commit()
    db.close()


def post_req_ccp(esi_path, json_data):
    url = "https://esi.evetech.net/latest/" + esi_path + "?datasource=tranquility"
    try:
        start_time = time.time()
        headers = {'User-Agent': 'HawkEye, Author: Kain Tarr'}
        r = requests.post(url, json_data, headers=headers)
        Logger.info('Requested {} and got it in {} seconds'.format(url, round(time.time() - start_time, 3)))
    except requests.exceptions.ConnectionError:
        Logger.info("No network connection.", exc_info=True)
        statusmsg.push_status("NETWORK ERROR: Check your internet connection and firewall settings.". app)
        time.sleep(5)
        return "network_error"
    if r.status_code != 200:
        try:
            server_msg = json.loads(r.text)["error"]
        except json.decoder.JSONDecodeError:
            Logger.error('Failed to return {}'.format(url))
        Logger.info("CCP Servers at (" + esi_path + ") returned error code: " + str(r.status_code) + ", saying: " + server_msg, exc_info=True)
        statusmsg.push_status("CCP SERVER ERROR: " + str(r.status_code) + " (" + server_msg + ")")
        return "server_error"
    return r.json()
