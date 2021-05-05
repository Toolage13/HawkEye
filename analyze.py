import asyncio
from aiohttp import ClientSession
import config
import json
import logging
import os
import random
import statusmsg
import time

Logger = logging.getLogger(__name__)

if not os.path.exists(os.path.join(config.PREF_PATH, 'kills/')):
    os.makedirs(os.path.join(config.PREF_PATH, 'kills/'))


def main(pilot_names, db):
    statusmsg.push_status("Retrieving pilot IDs from pilot names...")
    loop = asyncio.new_event_loop()
    loop.run_until_complete(resolve_pilot_ids(pilot_names, db))
    loop.close()
    statusmsg.push_status("Updating pilot corporations and alliances...")
    pilot_ids = db.query_characters(pilot_names)
    affiliations = db.get_char_affiliations(pilot_ids)
    affil_ids = []
    for a in affiliations:
        affil_ids.append(a.get('alliance_id'))
        affil_ids.append(a.get('corporation_id'))
    statusmsg.push_status("Updating corporation and alliance names from corporation and alliance IDs...")
    db.get_affil_names(affil_ids)
    character_stats = []
    for chunk in divide_chunks(pilot_names, config.MAX_CHUNK):
        statusmsg.push_status("Retrieving killboard data for {}...".format(', '.join(chunk)))
        Logger.info('Running chunk {}'.format(chunk))
        start_time = time.time()
        loop = asyncio.new_event_loop()
        details = loop.run_until_complete(concurrent_run_character(chunk, db))
        loop.close()
        for c in details:
            character_stats.append(c)
        Logger.info('Ran chunk in {} seconds.'.format(time.time() - start_time))
    return character_stats


def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


async def resolve_pilot_ids(pilot_names, db):
    coros = [db.get_pilot_id(p) for p in pilot_names]
    await asyncio.gather(*coros)


async def concurrent_run_character(pilot_names, db):
    coros = [get_kill_data(p, db) for p in pilot_names]
    return await asyncio.gather(*coros)


async def get_kill_data(pilot_name, db):
    Logger.info('Getting kill data for {}.'.format(pilot_name))
    pilot_id = await db.get_pilot_id(pilot_name)
    stats = {
        'alliance_id': 0,
        'alliance_name': 'None',
        'autz': {'kills': 0.01, 'attackers': 0},
        'average_kill_value': 0,
        'average_pilots': 0,
        'blops_use': 0,
        'boy_scout': 0,
        'buttbuddies': {},
        'capital_use': 0,
        'coastal_city_elite': 0,
        'corp_id': 0,
        'corp_name': '',
        'countryside_hillbilly': 0,
        'cyno': 0,
        'dream_crusher': 0,
        'eutz': {'kills': 0.01, 'attackers': 0},
        'gopnik': 0,
        'heavy_hitter': 0,
        'hotdrop': 0,
        'id': pilot_id,
        'involved_pilots': [],
        'name': pilot_name,
        'nanofag': 0,
        'playstyle': 'None',
        'processed_killmails': 0,
        'roleplaying_dock_workers': 0,
        'timezone': 'N/A',
        'top_regions': {},
        'top_ships': {},
        'trash_can_resident': 0,
        'ustz': {'kills': 0.01, 'attackers': 0},
        'vietcong': 0,
        'warning': ''
    }

    if not pilot_id:
        return stats

    affil_ids = db.get_char_affiliations([pilot_id])
    stats['corp_id'] = affil_ids[0]['corporation_id']
    stats['alliance_id'] = affil_ids[0].get('alliance_id')
    affiliations = db.get_affil_names([affil_ids[0]['corporation_id'], affil_ids[0].get('alliance_id')])

    for d in affiliations:
        if affil_ids[0]['corporation_id'] == d['id']:
            stats['corp_name'] = d['name']
        if affil_ids[0].get('alliance_id') == d['id']:
            stats['alliance_name'] = d['name']

    url = "https://zkillboard.com/api/kills/characterID/{}/page/{}/".format(pilot_id, 1)
    headers = {'Accept-Encoding': 'gzip', 'User-Agent': 'HawkEye, Author: Kain Tarr'}
    start_time = time.time()
    async with ClientSession() as session:
        retry = 0
        data = None
        while True:
            # Logger.info('Attempt {} for pilot {}.'.format(retry, pilot_name))
            if retry == config.ZKILL_RETRY:
                break
            try:
                async with session.get(url, headers=headers) as resp:
                    await asyncio.sleep(random.random() * config.ZKILL_MULTIPLIER)
                    text = await resp.text()
                    if text == "[]":
                        Logger.info('Returning empty killboard for {}'.format(pilot_name))
                        return stats
                    data = await resp.json()
                break
            except Exception as e:
                Logger.error('Failed to get kills page for {} : {}'.format(pilot_name, url))
                retry += 1
                await asyncio.sleep(random.random() * config.ZKILL_MULTIPLIER)

    if not data:
        stats['name'] = 'ZKILL RATE LIMITED (429)'
        return stats

    Logger.info('Requested {} and got it in {} seconds'.format(url, round(time.time() - start_time, 3)))

    Logger.info('Retrieving killmail data from CCP ESI for {}'.format(pilot_name))
    data = data[:config.MAX_KM]
    details = await process(data)

    for killmail in details:
        stats['processed_killmails'] += 1
        add_to_dict(stats['top_regions'], db.get_region(killmail['solar_system_id']))
        stats['average_pilots'] += len(killmail['attackers'])
        stats['average_kill_value'] += float(killmail['zkb']['totalValue'])
        stats[db.get_location(killmail['solar_system_id'])] += 1
        stats[get_timezone(killmail['killmail_time'])]['kills'] += 1
        stats[get_timezone(killmail['killmail_time'])]['attackers'] += len(killmail['attackers'])

        for attacker in killmail['attackers']:
            attacker_id = attacker.get('character_id')
            if attacker_id == pilot_id:
                add_to_dict(stats['top_ships'], attacker.get('ship_type_id'))
            else:
                add_to_dict(stats['buttbuddies'], attacker_id)
        if db.used_cyno(killmail['attackers'], pilot_id):
            stats['cyno'] += 1
        if db.used_capital(killmail['attackers'], pilot_id):
            stats['capital_use'] += 1
        if db.used_blops(killmail['attackers'], pilot_id):
            stats['blops_use'] += 1
        if db.used_smartbomb(killmail['attackers'], pilot_id):
            stats['roleplaying_dock_workers'] += 1

    stats['average_kill_value'] = stats['average_kill_value'] / (len(details) + 0.01)
    stats['average_pilots'] = round(stats['average_pilots'] / (len(details) + 0.01))
    for tz in ['autz', 'eutz', 'ustz']:
        stats[tz]['attackers'] = round(stats[tz]['attackers'] / stats[tz]['kills'])
    stats['timezone'] = 'AUTZ: {}% ({}) | EUTZ: {}% ({}) | USTZ: {}% ({})'.format(
        round(stats['autz']['kills'] / (stats['processed_killmails'] + 0.01) * 100), stats['autz']['attackers'],
        round(stats['eutz']['kills'] / (stats['processed_killmails'] + 0.01) * 100), stats['eutz']['attackers'],
        round(stats['ustz']['kills'] / (stats['processed_killmails'] + 0.01) * 100), stats['ustz']['attackers'])

    #start_time = time.time()
    #Logger.info('Got buddies in {} seconds.'.format(round(time.time() - start_time, 2)))

    stats['top_regions'] = ', '.join(get_top_three(stats['top_regions']))
    stats['top_ships'] = ', '.join(db.get_ship_name(i) for i in get_top_three(stats['top_ships']))
    stats['cyno'] = stats['cyno'] / (stats['processed_killmails'] + 0.01)
    stats['capital_use'] = '{}'.format(round(stats['capital_use'] / (stats['processed_killmails'] + 0.01) * 100))
    stats['blops_use'] = stats['blops_use'] / (stats['processed_killmails'] + 0.01)
    if stats['blops_use'] > config.BLOPS_HL_PERCENTAGE:
        stats['warning'] += "BLOPS"
    if stats['cyno'] > config.CYNO_HL_PERCENTAGE:
        if stats['warning'] == '':
            stats['warning'] = 'CYNO'
        else:
            stats['warning'] += " + CYNO"
    return stats


async def process(data):
    """
    :param data: zkill data
    :return: None
    """
    result_killmails = []
    start_time = time.time()
    async with ClientSession() as session:
        for d in data:
            att = asyncio.ensure_future(fetch(d, session))
            result_killmails.append(att)

        results = await asyncio.gather(*result_killmails)
    Logger.info('Gathered {} killmails from CCP servers in {} seconds'.format(len(data), time.time() - start_time))
    json_results = []
    for l in results:
        try:
            json_results.append(json.loads(l))
        except:
            json_results.append(l)
            pass
    for j in json_results:
        Logger.debug('Parsing {}'.format(j))
        try:
            if not os.path.exists(os.path.join(config.PREF_PATH, 'kills/{}.json'.format(str(j['killmail_id'])))):
                with open(os.path.join(config.PREF_PATH, 'kills/{}.json'.format(str(j['killmail_id']))), 'w') as file:
                    json.dump(j, file)
        except:
            Logger.error('Could not get killmail_id from {}'.format(j))
            json_results.remove(j)

    merged_kills = []
    for zkill in data:
        for ccpkill in json_results:
            if ccpkill is not None and zkill['killmail_id'] == ccpkill.get('killmail_id'):
                new_dict = {}
                for key in zkill.keys():
                    new_dict[key] = zkill[key]
                for key in ccpkill.keys():
                    new_dict[key] = ccpkill[key]
                merged_kills.append(new_dict)
    return merged_kills


async def fetch(d, session):
    """
    :param d:
    :param session:
    :return: json response parsed into dictionary
    """

    try:
        with open(os.path.join(config.PREF_PATH, 'kills/{}.json'.format(str(d['killmail_id']))), 'r') as json_file:
            return json.load(json_file)
    except:
        pass
        # Logger.info('Failed to open {}.json'.format(str(d['killmail_id'])))

    url = "https://esi.evetech.net/v1/killmails/{}/{}/?datasource=tranquility".format(d['killmail_id'], d['zkb']['hash'])
    try:
        async with session.get(url) as response:
            return await response.read()
    except Exception as e:
        Logger.error(e)


def add_to_dict(dict, key):
    if dict.get(key):
        dict[key] += 1
    else:
        dict[key] = 1


def get_timezone(time):
    time = time.split('T')[1].split(':')
    if int(time[0]) < 6:
        return 'ustz'
    if int(time[0]) < 14:
        return 'autz'
    return 'eutz'


def get_top_three(d):
    try:
        categories = list(d.keys())
        sorted_categories = [categories[0]]
        for r in categories:
            for s in sorted_categories:
                if d[r] > d[s]:
                    sorted_categories.insert(sorted_categories.index(s), r)
                    break
            if r not in sorted_categories:
                sorted_categories.append(r)
        while len(sorted_categories) < 3:
            sorted_categories.append('')
        return sorted_categories[:3]
    except:
        return ['', '', '']
