# !/usr/local/bin/python3.8
# Github: https://github.com/Toolage13/HawkEye
"""
This is the big boy that handles all the fetching of data, and analysis of the fetched data.
"""
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


def main(pilot_names, db):
    filtered_pilot_data = _filter_pilots(pilot_names, db)

    if len(filtered_pilot_data) == 0:
        Logger.info('Filtered out all pilots provided...')
        return None

    character_stats = []
    for chunk in divide_chunks(filtered_pilot_data, config.MAX_CHUNK):
        statusmsg.push_status("Retrieving killboard data for {}...".format(', '.join([c['pilot_name'] for c in chunk])))
        Logger.info('Running {} pilots through concurrent_run_character(...)'.format(len(chunk)))
        start_time = time.time()
        loop = asyncio.new_event_loop()
        details = loop.run_until_complete(_concurrent_run_character(chunk, db))
        loop.close()
        for c in details:
            character_stats.append(c)
        statusmsg.push_status('Ran {} pilots in {} seconds.'.format(len(chunk), round(time.time() - start_time, 2)))
        Logger.info('Ran {} pilots in {} seconds.'.format(len(chunk), round(time.time() - start_time, 2)))
    return character_stats, len(filtered_pilot_data) - len(pilot_names)


def _filter_pilots(pilot_names, db):
    """
    Get ignoredList from config, filter our list of pilot_names based on the pilot names stored in ignoredList
    :param pilot_names: List of pilot names
    :param db: EveDB object to run queries on
    :return: Filtered list
    """
    ignore_list = config.OPTIONS_OBJECT.Get("ignoredList", default=[])
    filtered_by_name = [p for p in pilot_names if p not in [i[1] for i in ignore_list]]
    if len(filtered_by_name) == 0:
        return []

    loop = asyncio.new_event_loop()
    pilot_map = loop.run_until_complete(_get_pilot_ids(filtered_by_name, db))
    loop.close()

    pilot_affiliations = db.get_pilot_affiliations(pilot_map)
    return [p for p in pilot_affiliations if p['corp_id'] not in [i[0] for i in ignore_list] and p['alliance_id'] not in [i[0] for i in ignore_list]]


async def _get_pilot_ids(pilot_names, db):
    """
    Gather pilot IDs by calling db.get_pilot_id() asynchronously
    :param pilot_names: List of pilot names
    :param db: EveDB object to run queries on
    :return: List of pilot IDs
    """
    coros = [db.get_pilot_id(p) for p in pilot_names]
    return await asyncio.gather(*coros)


def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]


async def _concurrent_run_character(pilot_chunk, db):
    coros = [_get_kill_data(p, db) for p in pilot_chunk]
    return await asyncio.gather(*coros)


async def _get_kill_data(pilot_data, db):
    Logger.info('Getting kill data for {}.'.format(pilot_data['pilot_name']))
    stats = {
        'alliance_id': pilot_data['alliance_id'],
        'alliance_name': pilot_data['alliance_name'],
        'autz': {'kills': 0.01, 'attackers': 0},
        'average_kill_value': 0,
        'average_pilots': 0,
        'avg_10': 0,
        'avg_gang': 0,
        'blops_use': 0,
        'boy_scout': 0,
        'buttbuddies': {},
        'capital_use': 0,
        'coastal_city_elite': 0,
        'corp_id': pilot_data['corp_id'],
        'corp_name': pilot_data['corp_name'],
        'countryside_hillbilly': 0,
        'cyno': 0,
        'dream_crusher': 0,
        'eutz': {'kills': 0.01, 'attackers': 0},
        'gopnik': 0,
        'heavy_hitter': 0,
        'hotdrop': 0,
        'involved_pilots': [],
        'nanofag': 0,
        'pilot_id': pilot_data['pilot_id'],
        'pilot_name': pilot_data['pilot_name'],
        'playstyle': 'None',
        'pro_10': 0,
        'pro_gang': 0,
        'processed_killmails': 0,
        'roleplaying_dock_workers': 0,
        'super': 0,
        'timezone': 'N/A',
        'titan': 0,
        'top_10_ships': None,
        'top_gang_ships': None,
        'top_regions': None,
        'top_ships': None,
        'trash_can_resident': 0,
        'ustz': {'kills': 0.01, 'attackers': 0},
        'vietcong': 0,
        'warning': ''
    }

    zkill_data = await _get_zkill_data(pilot_data['pilot_id'], pilot_data['pilot_name'])

    if not zkill_data:
        stats['name'] = 'ZKILL-MISSING'
        return stats

    zkill_data = zkill_data[:config.MAX_KM]
    merged_kills = await _merge_zkill_ccp_kills(zkill_data)

    return _prepare_stats(stats, merged_kills, db, pilot_data['pilot_id'])


async def _get_zkill_data(pilot_id, pilot_name):
    url = "https://zkillboard.com/api/kills/characterID/{}/page/{}/".format(pilot_id, 1)
    headers = {'Accept-Encoding': 'gzip', 'User-Agent': 'HawkEye, Author: Kain Tarr'}
    statusmsg.push_status('Requesting {}'.format(url))
    Logger.info('Requesting {}'.format(url))
    start_time = time.time()
    async with ClientSession() as session:
        retry = 0
        data = None
        while True:
            if retry == config.ZKILL_RETRY:
                break
            try:
                async with session.get(url, headers=headers) as resp:
                    await asyncio.sleep(random.random() * config.ZKILL_MULTIPLIER)
                    text = await resp.text()
                    if text == "[]":
                        Logger.info('Returning empty killboard for {}'.format(pilot_name))
                        return data
                    data = await resp.json()
                break
            except Exception as e:
                Logger.error('Failed to get kills page for {} : {}'.format(pilot_name, url))
                retry += 1
                await asyncio.sleep(random.random() * config.ZKILL_MULTIPLIER)
    statusmsg.push_status('Requested {} and got it in {} seconds'.format(url, round(time.time() - start_time, 2)))
    Logger.info('Requested {} and got it in {} seconds'.format(url, round(time.time() - start_time, 2)))
    return data


async def _merge_zkill_ccp_kills(data):
    """
    :param data: zkill data
    :return: None
    """
    if not os.path.exists(os.path.join(config.PREF_PATH, 'kills/')):
        os.makedirs(os.path.join(config.PREF_PATH, 'kills/'))

    result_killmails = []

    for zkill in data:
        r = _fetch_local(zkill['killmail_id'])
        if r:
            new_dict = {}
            for k in zkill:
                new_dict[k] = zkill[k]
            for k in r:
                new_dict[k] = r[k]
            result_killmails.append(new_dict)
    data[:] = [z for z in data if z['killmail_id'] not in [d['killmail_id'] for d in result_killmails]]
    Logger.info('Got {} killmails from local cache.'.format(len(result_killmails)))

    ccp_kills = []
    if len(data) > 0:
        statusmsg.push_status('Gathering {} killmails from CCP servers.'.format(len(data)))
        Logger.info('Gathering {} killmails from CCP servers.'.format(len(data)))
        start_time = time.time()
        async with ClientSession() as session:
            for d in data:
                att = asyncio.ensure_future(_fetch(d, session))
                ccp_kills.append(att)

            results = await asyncio.gather(*ccp_kills)
        statusmsg.push_status('Gathered {} killmails from CCP servers in {} seconds'.format(len(data), round(time.time() - start_time, 2)))
        Logger.info('Gathered {} killmails from CCP servers in {} seconds'.format(len(data), round(time.time() - start_time, 2)))

        results = [json.loads(kill) for kill in results]

        for zkill in data:
            for ccpkill in results:
                if zkill['killmail_id'] == ccpkill['killmail_id']:
                    new_dict = {}
                    for k in zkill:
                        new_dict[k] = zkill[k]
                    for k in ccpkill:
                        new_dict[k] = ccpkill[k]
                    result_killmails.append(new_dict)
    return result_killmails


def _fetch_local(killmail_id):
    try:
        with open(os.path.join(config.PREF_PATH, 'kills/{}.json'.format(killmail_id)), 'r') as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        return None


async def _fetch(d, session):
    """
    :param d:
    :param session:
    :return: json response parsed into dictionary
    """

    url = "https://esi.evetech.net/v1/killmails/{}/{}/?datasource=tranquility".format(d['killmail_id'], d['zkb']['hash'])
    while True:
        try:
            async with session.get(url) as response:
                r = await response.read()
                with open(os.path.join(config.PREF_PATH, 'kills/{}.json'.format(d['killmail_id'])), 'w') as file:
                    json.dump(json.loads(r), file)
                return r
        except Exception as e:
            Logger.error(e)
            await asyncio.sleep(0.25)


def _prepare_stats(stats, killmails, db, pilot_id):
    for killmail in killmails:
        stats['processed_killmails'] += 1
        stats['top_regions'] = _add_to_dict(stats['top_regions'], db.get_region(killmail['solar_system_id']))
        stats['average_pilots'] += len(killmail['attackers'])
        if len(killmail['attackers']) > 9:
            stats['avg_10'] += len(killmail['attackers'])
            stats['pro_10'] += 1
        else:
            stats['avg_gang'] += len(killmail['attackers'])
            stats['pro_gang'] += 1
        stats['average_kill_value'] += float(killmail['zkb']['totalValue'])
        stats[db.get_location(killmail['solar_system_id'])] += 1
        stats[_get_timezone(killmail['killmail_time'])]['kills'] += 1
        stats[_get_timezone(killmail['killmail_time'])]['attackers'] += len(killmail['attackers'])
        if db.killed_on_gate(killmail) and not(db.used_capital(killmail['attackers'], pilot_id)) and not(db.used_blops(killmail['attackers'], pilot_id)):
            stats['boy_scout'] += 1

        for attacker in killmail['attackers']:
            attacker_id = attacker.get('character_id')
            if attacker_id == pilot_id:
                stats['top_ships'] = _add_to_dict(stats['top_ships'], attacker.get('ship_type_id'))
                if len(killmail['attackers']) > 9:
                    stats['top_10_ships'] = _add_to_dict(stats['top_10_ships'], attacker.get('ship_type_id'))
                else:
                    stats['top_gang_ships'] = _add_to_dict(stats['top_gang_ships'], attacker.get('ship_type_id'))
            else:
                stats['buttbuddies'] = _add_to_dict(stats['buttbuddies'], attacker_id)
        if db.used_cyno(killmail['attackers'], pilot_id):
            stats['cyno'] += 1
        if db.used_capital(killmail['attackers'], pilot_id):
            stats['capital_use'] += 1
        if db.used_blops(killmail['attackers'], pilot_id):
            stats['blops_use'] += 1
        if db.used_smartbomb(killmail['attackers'], pilot_id):
            stats['roleplaying_dock_workers'] += 1
        if db.used_super(killmail['attackers'], pilot_id):
            stats['super'] += 1
        if db.used_titan(killmail['attackers'], pilot_id):
            stats['titan'] += 1

    stats['average_kill_value'] = stats['average_kill_value'] / (stats['processed_killmails'] + 0.01)
    stats['average_pilots'] = round(stats['average_pilots'] / (stats['processed_killmails'] + 0.01))
    stats['avg_10'] = round(stats['avg_10'] / (stats['pro_10'] + 0.01))
    stats['avg_gang'] = round(stats['avg_gang'] / (stats['pro_gang'] + 0.01))
    timezone = 'autz'
    for tz in ['eutz', 'ustz']:
        if stats[tz]['kills'] > stats[timezone]['kills']:
            timezone = tz
    stats['timezone'] = '{}: {}% ({})'.format(timezone.upper(),
                                              round(stats[timezone]['kills'] / (stats['processed_killmails'] + 0.01) * 100),
                                              stats['average_pilots']
                                              )
    stats['top_regions'] = ', '.join(r for r in _get_top_three(stats['top_regions']) if r is not None)
    stats['top_ships'] = ', '.join(s for s in [db.get_ship_name(i) for i in _get_top_three(stats['top_ships'])] if s is not None)
    stats['top_10_ships'] = ', '.join(s for s in [db.get_ship_name(i) for i in _get_top_three(stats['top_10_ships'])] if s is not None)
    stats['top_gang_ships'] = ', '.join(s for s in [db.get_ship_name(i) for i in _get_top_three(stats['top_gang_ships'])] if s is not None)
    stats['cyno'] = stats['cyno'] / (stats['processed_killmails'] + 0.01)
    stats['capital_use'] = stats['capital_use'] / (stats['processed_killmails'] + 0.01)
    stats['blops_use'] = stats['blops_use'] / (stats['processed_killmails'] + 0.01)
    stats['roleplaying_dock_workers'] = stats['roleplaying_dock_workers'] / (stats['processed_killmails'] + 0.01)
    if stats['blops_use'] > config.BLOPS_HL_PERCENTAGE:
        stats['warning'] = _add_string(stats['warning'], 'BLOPS')
    if stats['cyno'] > config.CYNO_HL_PERCENTAGE:
        stats['warning'] = _add_string(stats['warning'], 'CYNO')
    if stats['super'] > 0:
        stats['warning'] = _add_string(stats['warning'], 'SUPER')
    if stats['titan'] > 0:
        stats['warning'] = _add_string(stats['warning'], 'TITAN')
    if stats['roleplaying_dock_workers'] > config.SB_HL_PERCENTAGE:
        stats['warning'] = _add_string(stats['warning'], 'SMARTBOMB')
    return stats


def _add_to_dict(dict, key):
    try:
        if dict.get(key):
            dict[key] += 1
        else:
            dict[key] = 1
    except AttributeError:
        return {key: 1}
    return dict


def _get_timezone(time):
    time = time.split('T')[1].split(':')
    if int(time[0]) < 6:
        return 'ustz'
    if int(time[0]) < 14:
        return 'autz'
    return 'eutz'


def _get_top_three(d):
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


def _add_string(o, n):
    if o == '':
        return n
    return '{} + {}'.format(o, n)
