# !/usr/local/bin/python3.8
# Github: https://github.com/Toolage13/HawkEye
"""
This is the big boy that handles all the fetching of data, and analysis of the fetched data.
"""
import asyncio
from aiohttp import ClientSession
import datetime
import eveDB
import config
import json
import logging
import os
import random
import statusmsg
import time

Logger = logging.getLogger(__name__)


def main(pilot_names, populate_all):
    """
    The main method takes the list of pilot_names, filters and then transforms it into a list of dictionaries
    containing pilot data using _filter_pilots(). The list is then broken into chunks of size config.MAX_CHUNK and
    the chunks passed through _concurrent_run_characters(), the result of this is a list of dictionaries containing
    expanded pilot data. Each dictionary is appended to character_stats, which is finally returned.
    :param pilot_names: A list of pilot names to parse
    :param populate_all: Whether to just grab pilot name and associations, or all data.
    :return character_stats: A list of dictionaries containing expanded pilot data
    """
    with eveDB.EveDB() as db:
        filtered_pilot_data = _filter_pilots(pilot_names, db)
        if not populate_all:
            character_stats = []
            for pilot in filtered_pilot_data:
                character_stats.append(_get_stats_dictionary(pilot, True))
            return character_stats, len(filtered_pilot_data) - len(pilot_names)

        if len(filtered_pilot_data) == 0:
            Logger.warning('Filtered out all pilots provided...')
            statusmsg.push_status("Filtered out all pilots provided...")
            return None

        character_stats = []
        for chunk in divide_chunks(filtered_pilot_data, config.MAX_CHUNK):
            statusmsg.push_status("Retrieving killboard data for {}...".format(', '.join([c['pilot_name'] for c in chunk])))
            Logger.info('Running {} pilots through concurrent_run_character(...)'.format(len(chunk)))
            start_time = time.time()
            loop = asyncio.new_event_loop()
            details = loop.run_until_complete(_concurrent_run_character(chunk, db, 'kills'))
            loop.close()
            for c in details:
                character_stats.append(c)
            statusmsg.push_status('Ran {} pilots in {} seconds.'.format(len(chunk), round(time.time() - start_time, 2)))
            Logger.info('Ran {} pilots in {} seconds.'.format(len(chunk), round(time.time() - start_time, 2)))

            loop = asyncio.new_event_loop()
            details = loop.run_until_complete(_concurrent_run_character(chunk, db, 'losses'))
            loop.close()
            for c in details:
                for e in character_stats:
                    if c['pilot_id'] == e['pilot_id']:
                        for k in c:
                            e[k] = c[k]
                        break

        return character_stats, len(filtered_pilot_data) - len(pilot_names)


def _filter_pilots(pilot_names, db):
    """
    Get ignoredList from config, filter our list of pilot_names based on the pilot names stored in ignoredList
    Get pilot_map with _get_pilot_ids() containing dictionaries with both pilot_id and pilot_name
    Get pilot_affiliations with db.get_pilot_affiliations() which contains additional pilot_data (corp and alliance)
    :param pilot_names: List of pilot names
    :param db: EveDB object to run queries on
    :return: Filtered list
    """
    ignore_list = config.OPTIONS_OBJECT.Get("ignoredList", default=[])
    filtered_by_name = [p for p in pilot_names if p not in [i[1] for i in ignore_list]]
    if len(filtered_by_name) == 0:
        return []

    start_time = time.time()
    Logger.info('Retrieving {} pilot IDs from CCP...'.format(len(filtered_by_name)))
    statusmsg.push_status('Retrieving {} pilot IDs from CCP...'.format(len(filtered_by_name)))
    loop = asyncio.new_event_loop()
    pilot_map = loop.run_until_complete(_get_pilot_ids(filtered_by_name, db))
    loop.close()
    logging.info('Retrieved {} pilot IDs from CCP in {} seconds.'.format(len(filtered_by_name),
                                                                         round(time.time() - start_time, 2)))
    statusmsg.push_status('Retrieved {} pilot IDs from CCP in {} seconds.'.format(len(filtered_by_name),
                                                                                  round(time.time() - start_time, 2)))

    pilot_affiliations = db.get_pilot_affiliations([p for p in pilot_map if p is not None])
    return [p for p in pilot_affiliations if p['corp_id'] not in [i[0] for i in ignore_list] and
            p['alliance_id'] not in [i[0] for i in ignore_list]]


async def _get_pilot_ids(pilot_names, db):
    """
    Gather pilot IDs by calling db.get_pilot_id() asynchronously
    :param pilot_names: List of pilot names
    :param db: EveDB object to run queries on
    :return: List of dictionaries containing pilot_id and pilot_name
    """
    coros = [db.get_pilot_id(p) for p in pilot_names]
    return await asyncio.gather(*coros)


def divide_chunks(my_list, n):
    """
    Divide a list l into chunks of n size, yield each list as iterated
    :param my_list: Original list
    :param n: Size of chunks
    :yield: Each chunk
    """
    for i in range(0, len(my_list), n):
        yield my_list[i:i + n]


async def _concurrent_run_character(pilot_chunk, db, kills_loss):
    """
    Run pilot_data p through _get_kill_data() asynchronously and assemble all expanded pilot data via asyncio.gather()
    :param pilot_chunk: List of pilot data stored as dictionaries
    :param db: EveDB to use
    :return: List of dictionaries containing expanded pilot data
    """
    if kills_loss == 'kills':
        coros = [_get_kill_data(p, db) for p in pilot_chunk]
    if kills_loss == 'losses':
        coros = [_get_loss_data(p, db) for p in pilot_chunk]
    return await asyncio.gather(*coros)


async def _get_kill_data(pilot_data, db):
    """
    Return zkill data for pilot using _get_zkill_data(). Merge with kill data from CCP fetched with
    _merge_zkill_ccp_kills(). Finally, pass to _prepare_stats() for final processing and then return
    :param pilot_data: Dictionary of pilot data
    :param db: EveDB object to use
    :return: Dictionary of expanded pilot data
    """
    start_time = time.time()
    zkill_data = await _get_zkill_data('kills', pilot_data['pilot_id'], pilot_data['pilot_name'])

    if not zkill_data:
        stats = _get_stats_dictionary(pilot_data, ret_blank=True)
        stats['process_time'] = time.time() - start_time
        stats['query'] = True
        return stats

    zkill_data = zkill_data[:config.OPTIONS_OBJECT.Get("maxKillmails", default=50)]
    merged_kills = await _merge_zkill_ccp_kills(zkill_data)

    Logger.info("Retrieved kills data for {} in {} seconds.".format(pilot_data['pilot_name'], round(time.time() - start_time, 2)))
    stats = _prepare_stats(pilot_data, merged_kills, db)
    stats['process_time'] = time.time() - start_time
    return stats


async def _get_zkill_data(page, pilot_id, pilot_name):
    """
    Request zkillboard page 1 from zkill for pilot_id, retry up to config.ZKILL_RETRY times with a brief delay between
    requests of asyncio.sleep() * config.ZKILL_MULTIPLIER. If the pilot has no zkill, zkill returns an empty list []
    and we return None for data. If data is still None after config.ZKILL_RETRY retries, return None
    :param pilot_id: Pilot ID
    :param pilot_name: Pilot name
    :return: Data if retrieved, otherwise None
    """
    url = "https://zkillboard.com/api/{}/characterID/{}/page/{}/".format(page, pilot_id, 1)
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
                Logger.warning('Failed to get kills page for {} : {}'.format(pilot_name, url))
                retry += 1
                await asyncio.sleep(random.random() * config.ZKILL_MULTIPLIER)
    statusmsg.push_status('Requested {} and got it in {} seconds'.format(url, round(time.time() - start_time, 2)))
    Logger.info('Requested {} and got it in {} seconds'.format(url, round(time.time() - start_time, 2)))
    return data


def _get_stats_dictionary(pilot_data, ret_blank=False):
    stats = {
        'alliance_id': pilot_data['alliance_id'],
        'alliance_name': pilot_data['alliance_name'],
        'associates': {},
        'autz': {'kills': 0.01, 'attackers': 0},
        'average_kill_value': 0,
        'average_pilots': 0,
        'avg_10': 0,
        'avg_gang': 0,
        'blops_use': 0,
        'boy_scout': 0,
        'buttbuddies': {},
        'capital_use': 0,
        'corp_id': pilot_data['corp_id'],
        'corp_name': pilot_data['corp_name'],
        'cyno': 0,
        'eutz': {'kills': 0.01, 'attackers': 0},
        'highsec': 0,
        'lowsec': 0,
        'nullsec': 0,
        'last_five_kills': [],
        'last_kill': None,
        'last_kill_attackers': None,
        'last_used_ship': None,
        'pilot_id': pilot_data['pilot_id'],
        'pilot_name': pilot_data['pilot_name'],
        'playstyle': 'None',
        'pro_10': 0,
        'pro_gang': 0,
        'processed_killmails': 0,
        'query': True,
        'smartbomb': 0,
        'super': 0,
        'timezone': 'N/A',
        'titan': 0,
        'top_10_ships': None,
        'top_gang_ships': None,
        'top_regions': None,
        'top_ships': None,
        'top_space': {},
        'ustz': {'kills': 0.01, 'attackers': 0},
        'warning': '',
        'wormhole': 0
    }
    if ret_blank:
        stats['associates'] = None
        stats['buttbuddies'] = None
        stats['ordered_losses'] = None
        stats['query'] = False
        stats['top_space'] = None
        stats['warning'] = None
    return stats


async def _merge_zkill_ccp_kills(data):
    """
    Try to fetch kills locally using _fetch_local() if available and store them in result_killmails. Rehash data to
    remove the killmails that were found locally. Pass the remaining killmails as data to CCP via _fetch(). Finally,
    merge the zkill data with the CCP kill data, matching on killmail_id and merging into a list of dictionaries
    :param data: zkill data
    :return: The merged killmail data from zkill and CCP as result_killmails
    """
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
                att = asyncio.ensure_future(_fetch(d['killmail_id'], d['zkb']['hash'], session))
                ccp_kills.append(att)

            results = await asyncio.gather(*ccp_kills)
        statusmsg.push_status('Gathered {} killmails from CCP servers in {} seconds'.format(
            len(data), round(time.time() - start_time, 2)))
        Logger.info('Gathered {} killmails from CCP servers in {} seconds'.format(
            len(data), round(time.time() - start_time, 2)))

        for zkill in data:
            for ccpkill in results:
                try:
                    if zkill['killmail_id'] == ccpkill['killmail_id']:
                        new_dict = {}
                        for k in zkill:
                            new_dict[k] = zkill[k]
                        for k in ccpkill:
                            new_dict[k] = ccpkill[k]
                        result_killmails.append(new_dict)
                except Exception as e:
                    Logger.error(zkill)
                    Logger.error(ccpkill)
                    raise e
    return result_killmails


def _fetch_local(killmail_id):
    """
    Try to fetch a killmail locally (stored as json)
    :param killmail_id: Killmail ID
    :return: json file if found, otherwise None
    """
    try:
        with open(os.path.join(config.PREF_PATH, 'kills/{}.json'.format(killmail_id)), 'r') as json_file:
            return json.load(json_file)
    except FileNotFoundError:
        return None


async def _fetch(killmail_id, killhash, session):
    """
    Fetch killmail from CCP servers.
    :param killmail_id: Killmail ID
    :param killhash: Killmail hash
    :param session: Session to use
    :return: json response parsed into dictionary
    """

    url = "https://esi.evetech.net/v1/killmails/{}/{}/?datasource=tranquility".format(killmail_id, killhash)
    while True:
        async with session.get(url) as response:
            r = await response.read()
            try:
                j = json.loads(r)
            except json.decoder.JSONDecodeError:
                await asyncio.sleep(0.25)
                continue
            if j.get('error'):
                await asyncio.sleep(0.25)
                continue
            with open(os.path.join(config.PREF_PATH, 'kills/{}.json'.format(killmail_id)), 'w') as file:
                json.dump(j, file)
            return j


def _prepare_stats(pilot_data, killmails, db):
    """
    Process a list of killmails stored as dictionaries, assign a lot of attributes to stats, then pass to
    _format_stats() for final calculations.
    :param pilot_data: Pilot data to use
    :param killmails: List of dictionaries containing killmails
    :param db: EveDB to use
    :return: Enriched stats
    """

    stats = _get_stats_dictionary(pilot_data)
    for killmail in killmails:
        stats['processed_killmails'] += 1
        # Valuations, fleet sizes, and ship types in small or large fleets
        stats['average_kill_value'] += float(killmail['zkb']['totalValue'])
        stats['average_pilots'] += len(killmail['attackers'])
        if len(killmail['attackers']) > 9:
            stats['avg_10'] += len(killmail['attackers'])
            stats['pro_10'] += 1
        else:
            stats['avg_gang'] += len(killmail['attackers'])
            stats['pro_gang'] += 1
        for attacker in killmail['attackers']:
            if attacker.get('character_id') == pilot_data['pilot_id']:
                if stats['last_used_ship'] is None:
                    stats['last_used_ship'] = db.get_ship_name(attacker.get('ship_type_id'))
                    stats['last_kill_attackers'] = len(killmail['attackers'])
                stats['top_ships'] = _add_to_dict(stats['top_ships'], attacker.get('ship_type_id'))
                if len(killmail['attackers']) > 9:
                    stats['top_10_ships'] = _add_to_dict(stats['top_10_ships'], attacker.get('ship_type_id'))
                else:
                    stats['top_gang_ships'] = _add_to_dict(stats['top_gang_ships'], attacker.get('ship_type_id'))
            else:
                stats['buttbuddies'] = _add_to_dict(stats['buttbuddies'], attacker.get('character_id'))  # Not used, but maybe someday

        # Location and timezone
        stats['top_regions'] = _add_to_dict(stats['top_regions'], db.get_region(killmail['solar_system_id']))
        stats['top_space'] = _add_to_dict(stats['top_space'], db.get_location(killmail['solar_system_id']))
        stats[_get_timezone(killmail['killmail_time'])]['kills'] += 1
        stats[_get_timezone(killmail['killmail_time'])]['attackers'] += len(killmail['attackers'])

        # Add to our list of recent kills
        if len(stats['last_five_kills']) < 5:
            stats['last_five_kills'].append({
                # 'victim': db.get_pilot_name(killmail['victim'].get('character_id')),
                'victim_ship': db.get_ship_name(killmail['victim']['ship_type_id']),
                'attackers': len(killmail['attackers']),
                'killed_when': (datetime.date.today() - datetime.datetime.strptime(
                    killmail['killmail_time'].split('T')[0], '%Y-%m-%d').date()).days,
                'killmail_time': datetime.datetime.strptime(killmail['killmail_time'].split('T')[0], '%Y-%m-%d')
            })

        # Kill attributes (using certain ships etc.)
        if db.killed_on_gate(killmail) and not(db.used_capital(killmail['attackers'], pilot_data['pilot_id'])) and not(
                db.used_blops(killmail['attackers'], pilot_data['pilot_id'])):
            stats['boy_scout'] += 1  # Gatecamping
        if db.used_cyno(killmail['attackers'], pilot_data['pilot_id']):
            stats['cyno'] += 1
        if db.used_capital(killmail['attackers'], pilot_data['pilot_id']):
            stats['capital_use'] += 1
        if db.used_blops(killmail['attackers'], pilot_data['pilot_id']):
            stats['blops_use'] += 1
        if db.used_smartbomb(killmail['attackers'], pilot_data['pilot_id']):
            stats['smartbomb'] += 1
        if db.used_super(killmail['attackers'], pilot_data['pilot_id']):
            stats['super'] += 1
        if db.used_titan(killmail['attackers'], pilot_data['pilot_id']):
            stats['titan'] += 1

        # Associates
        for attacker in killmail['attackers']:
            if attacker.get('character_id') is not None and attacker.get(
                    'character_id') != pilot_data['pilot_id'] and attacker.get(
                        'corp_id') != pilot_data['corp_id'] and attacker.get('alliance_id') != pilot_data['alliance_id']:
                _add_to_dict(stats['associates'], attacker.get('alliance_id') if attacker.get(
                    'alliance_id') else attacker['corporation_id'])

    return _format_stats(stats, db)


def _add_to_dict(my_dict, key):
    """
    Add 1 to a key if it exists in a dictionary, otherwise add it as a new key with value 1 to the dictionary, and
    return the dictionary.
    :param my_dict: Original dictionary
    :param key: Key to update/add
    :return: Return the updated dictionary
    """
    try:
        if my_dict.get(key):
            my_dict[key] += 1
        else:
            my_dict[key] = 1
    except AttributeError:
        return {key: 1}
    return my_dict


def _get_timezone(my_time):
    """
    Take a string timezone with CCP's weird formatting, determine timezone by the hour of the kill:
    00:00 - 06:00 USTZ
    06:00 - 14:00 AUTZ
    14:00 - 00:00 EUTZ
    :param my_time: Input time string
    :return: Timezone
    """
    my_time = my_time.split('T')[1].split(':')
    if int(my_time[0]) < 6:
        return 'ustz'
    if int(my_time[0]) < 14:
        return 'autz'
    return 'eutz'


def _format_stats(stats, db):
    """
    Make some calculations and other formatting changes to stats being passed.
    :param stats: Input statistics dictionary
    :param db: EveDB to use
    :return: Enriched stats
    """
    # Valuations, fleet sizes, and ship types in small or large fleets
    stats['average_kill_value'] = stats['average_kill_value'] / (stats['processed_killmails'] + 0.01)
    stats['average_pilots'] = round(stats['average_pilots'] / (stats['processed_killmails'] + 0.01))
    stats['avg_10'] = round(stats['avg_10'] / (stats['pro_10'] + 0.01))
    stats['avg_gang'] = round(stats['avg_gang'] / (stats['pro_gang'] + 0.01))
    stats['top_ships'] = ', '.join(
        s for s in [db.get_ship_name(i) for i in _get_top_three(stats['top_ships'])] if s is not None)
    stats['top_10_ships'] = ', '.join(
        s for s in [db.get_ship_name(i) for i in _get_top_three(stats['top_10_ships'])] if s is not None)
    stats['top_gang_ships'] = ', '.join(
        s for s in [db.get_ship_name(i) for i in _get_top_three(stats['top_gang_ships'])] if s is not None)

    # Location and timezone
    stats['top_regions'] = ', '.join(r for r in _get_top_three(stats['top_regions']) if r not in [None, ''])
    timezone = 'autz'
    for tz in ['eutz', 'ustz']:
        if stats[tz]['kills'] > stats[timezone]['kills']:
            timezone = tz
    stats['timezone'] = '{} {}% ({})'.format(timezone.upper(), round(
        stats[timezone]['kills'] / (stats['processed_killmails'] + 0.01) * 100), stats['average_pilots'])

    space_types = [t for t in ['highsec', 'lowsec', 'nullsec', 'wormhole'] if t in stats['top_space'].keys()]
    activity = space_types[0]
    for space in space_types:
        if stats['top_space'].get(space) > stats['top_space'].get(activity):
            activity = space
    stats['top_space'] = '{}{} ({}%)'.format(activity[0].upper(), activity[1:], round(
        stats['top_space'][activity] / (stats['processed_killmails'] + 0.01) * 100))

    # Recent kill details
    stats['last_kill'] = stats['last_five_kills'][0]['killed_when']

    # Kill attributes (using certain ships etc.)
    stats['cyno'] = stats['cyno'] / (stats['processed_killmails'] + 0.01)
    stats['capital_use'] = stats['capital_use'] / (stats['processed_killmails'] + 0.01)
    stats['blops_use'] = stats['blops_use'] / (stats['processed_killmails'] + 0.01)
    stats['smartbomb'] = stats['smartbomb'] / (stats['processed_killmails'] + 0.01)
    stats['boy_scout'] = stats['boy_scout'] / (stats['processed_killmails'] + 0.01)

    # Populate warnings
    if stats['titan'] > 0:
        stats['warning'] = _add_string(stats['warning'], 'TITAN')
    if stats['super'] > 0:
        stats['warning'] = _add_string(stats['warning'], 'SUPER')
    if stats['smartbomb'] > config.SB_HL_PERCENTAGE:
        stats['warning'] = _add_string(stats['warning'], 'SMARTBOMB')
    if stats['cyno'] > config.CYNO_HL_PERCENTAGE:
        stats['warning'] = _add_string(stats['warning'], 'CYNO')
    if stats['capital_use'] > config.CAP_HL_PERCENTAGE:
        stats['warning'] = _add_string(stats['warning'], 'CAP PILOT')
    if stats['blops_use'] > config.BLOPS_HL_PERCENTAGE:
        stats['warning'] = _add_string(stats['warning'], 'BLOPS')
    if stats['boy_scout'] > config.GATECAMP_HL_PERCENTAGE:
        stats['warning'] = _add_string(stats['warning'], 'GATECAMPER')

    # Associates
    stats['associates'] = _get_associates(stats['associates'], db)
    stats['associates'] = ', '.join(n for n in stats['associates'])
    return stats


def _get_top_three(d):
    """
    Return a list of the top three keys in a dictionary by comparing numeric values stored as values for each key
    :param d: Input dictionary
    :return: Top three sorted list if possible, otherwise list of three blank strings
    """
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


def _get_associates(associates, db):
    associates = _get_top_three(associates)
    affil_names = db.get_affil_names(associates)
    for entity_id in associates:
        for entity in affil_names:
            if entity_id == entity['id']:
                associates[associates.index(entity_id)] = entity['name']
    return associates


async def _get_loss_data(pilot_data, db):
    """
    Return zkill data for pilot using _get_zkill_data(). Merge with kill data from CCP fetched with
    _merge_zkill_ccp_kills(). Finally, pass to _prepare_stats() for final processing and then return
    :param pilot_data: Dictionary of pilot data
    :param db: EveDB object to use
    :return: Dictionary of expanded pilot data
    """
    zkill_data = await _get_zkill_data('losses', pilot_data['pilot_id'], pilot_data['pilot_name'])

    if not zkill_data:
        return _get_loss_stats(pilot_data, ret_blank=True)

    zkill_data = zkill_data[:config.OPTIONS_OBJECT.Get("maxKillmails", default=50)]
    merged_losses = await _merge_zkill_ccp_kills(zkill_data)

    stats = _prepare_loss_stats(pilot_data, merged_losses, db)
    return stats


def _get_loss_stats(pilot_data, ret_blank=False):
    stats = {
        'average_loss_value': 0,
        'last_five_losses': [],
        'last_loss': None,
        'last_lost_ship': None,
        'pilot_id': pilot_data['pilot_id'],
        'processed_lossmails': 0,
        'top_lost_ships': {}
    }
    if ret_blank:
        stats['top_lost_ships'] = None
    return stats


def _prepare_loss_stats(pilot_data, merged_losses, db):
    stats = _get_loss_stats(pilot_data)

    for loss in merged_losses:
        stats['processed_lossmails'] += 1
        stats['average_loss_value'] += float(loss['zkb']['totalValue'])

        if stats['last_lost_ship'] is None:
            stats['last_lost_ship'] = db.get_ship_name(loss['victim'].get('ship_type_id'))
            stats['last_loss_attackers'] = len(loss['attackers'])
        stats['top_lost_ships'] = _add_to_dict(stats['top_lost_ships'], db.get_ship_name(loss['victim'].get('ship_type_id')))

        if len(stats['last_five_losses']) < 5:
            stats['last_five_losses'].append({
                # 'victim': db.get_pilot_name(loss['victim'].get('character_id')),
                'victim_ship': db.get_ship_name(loss['victim']['ship_type_id']),
                'attackers': len(loss['attackers']),
                'killed_when': (datetime.date.today() - datetime.datetime.strptime(
                    loss['killmail_time'].split('T')[0], '%Y-%m-%d').date()).days,
                'killmail_time': datetime.datetime.strptime(loss['killmail_time'].split('T')[0], '%Y-%m-%d')
            })

    return _format_loss_stats(stats)


def _format_loss_stats(stats):
    stats['top_lost_ships'] = ', '.join(s for s in _get_top_three(stats['top_lost_ships']))
    stats['average_loss_value'] = stats['average_loss_value'] / (stats['processed_lossmails'] + 0.01)
    stats['last_loss'] = stats['last_five_losses'][0]['killed_when']
    return stats
