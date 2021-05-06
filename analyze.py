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
    ignore_list = config.OPTIONS_OBJECT.Get("ignoredList")
    Logger.info('Removing pilots {} from list to retrieve.'.format([p for p in pilot_names if p in [i[1] for i in ignore_list]]))
    new_pilot_names = [p for p in pilot_names if p not in [i[1] for i in ignore_list]]
    statusmsg.push_status("Retrieving pilot IDs from pilot names...")
    loop = asyncio.new_event_loop()
    loop.run_until_complete(resolve_pilot_ids(new_pilot_names, db))
    loop.close()
    pilot_ids = db.query_characters(new_pilot_names)
    transform_ignore = {i[0]: i[1] for i in ignore_list}
    for p in pilot_ids:
        if p['corp_id'] in transform_ignore.keys():
            Logger.info('Removing pilot {} from list to retrieve ({}).'.format(p['char_name'], transform_ignore[p['corp_id']]))
    pilot_ids = [p for p in pilot_ids if p['corp_id'] not in transform_ignore.keys()]
    for p in pilot_ids:
        if p['alliance_id'] in transform_ignore.keys():
            Logger.info(
                'Removing pilot {} from list to retrieve ({}).'.format(p['char_name'], transform_ignore[p['alliance_id']]))
    pilot_ids = [p for p in pilot_ids if p['alliance_id'] not in transform_ignore.keys()]
    if len(pilot_ids) == 0:
        Logger.info('Filtered out all pilots provided...')
        return None
    statusmsg.push_status("Updating pilot corporations and alliances...")
    affiliations = db.get_char_affiliations([p['char_id'] for p in pilot_ids])
    affil_ids = []
    for a in affiliations:
        affil_ids.append(a.get('alliance_id'))
        affil_ids.append(a.get('corporation_id'))
    statusmsg.push_status("Updating corporation and alliance names from corporation and alliance IDs...")
    db.get_affil_names(affil_ids)
    character_stats = []
    for chunk in divide_chunks(pilot_ids, config.MAX_CHUNK):
        statusmsg.push_status("Retrieving killboard data for {}...".format(', '.join([c['char_name'] for c in chunk])))
        Logger.info('Running chunk {}'.format(chunk))
        start_time = time.time()
        loop = asyncio.new_event_loop()
        details = loop.run_until_complete(concurrent_run_character(chunk, db))
        loop.close()
        for c in details:
            character_stats.append(c)
        Logger.info('Ran chunk in {} seconds.'.format(time.time() - start_time))
    return (character_stats, len(pilot_names) - len(pilot_ids))


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
    Logger.info('Getting kill data for {}.'.format(pilot_name['char_name']))
    pilot_id = await db.get_pilot_id(pilot_name['char_name'])
    stats = {
        'alliance_id': pilot_name['alliance_id'],
        'alliance_name': 'None',
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
        'corp_id': pilot_name['corp_id'],
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
        'name': pilot_name['char_name'],
        'nanofag': 0,
        'playstyle': 'None',
        'pro_10': 0,
        'pro_gang': 0,
        'processed_killmails': 0,
        'roleplaying_dock_workers': 0,
        'super': 0,
        'timezone': 'N/A',
        'titan': 0,
        'top_10_ships': {},
        'top_gang_ships': {},
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
                Logger.error('Failed to get kills page for {} : {}'.format(pilot_name['char_name'], url))
                retry += 1
                await asyncio.sleep(random.random() * config.ZKILL_MULTIPLIER)

    if not data:
        stats['name'] = 'ZKILL RATE LIMITED (429)'
        return stats

    Logger.info('Requested {} and got it in {} seconds'.format(url, round(time.time() - start_time, 3)))

    Logger.info('Retrieving killmail data from CCP ESI for {}'.format(pilot_name))
    data = data[:config.MAX_KM]
    details = await process(data, db)

    for killmail in details:
        stats['processed_killmails'] += 1
        add_to_dict(stats['top_regions'], db.get_region(killmail['solar_system_id']))
        stats['average_pilots'] += len(killmail['attackers'])
        if len(killmail['attackers']) > 9:
            stats['avg_10'] += len(killmail['attackers'])
            stats['pro_10'] += 1
        else:
            stats['avg_gang'] += len(killmail['attackers'])
            stats['pro_gang'] += 1
        stats['average_kill_value'] += float(killmail['zkb']['totalValue'])
        stats[db.get_location(killmail['solar_system_id'])] += 1
        stats[get_timezone(killmail['killmail_time'])]['kills'] += 1
        stats[get_timezone(killmail['killmail_time'])]['attackers'] += len(killmail['attackers'])
        if db.killed_on_gate(killmail) and not(db.used_capital(killmail['attackers'], pilot_id)) and not(db.used_blops(killmail['attackers'], pilot_id)):
            stats['boy_scout'] += 1

        for attacker in killmail['attackers']:
            attacker_id = attacker.get('character_id')
            if attacker_id == pilot_id:
                add_to_dict(stats['top_ships'], attacker.get('ship_type_id'))
                if len(killmail['attackers']) > 9:
                    add_to_dict(stats['top_10_ships'], attacker.get('ship_type_id'))
                else:
                    add_to_dict(stats['top_gang_ships'], attacker.get('ship_type_id'))
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
    stats['top_regions'] = ', '.join(get_top_three(stats['top_regions']))
    stats['top_ships'] = ', '.join(db.get_ship_name(i) for i in get_top_three(stats['top_ships']))
    stats['top_10_ships'] = ', '.join(db.get_ship_name(i) for i in get_top_three(stats['top_10_ships']))
    stats['top_gang_ships'] = ', '.join(db.get_ship_name(i) for i in get_top_three(stats['top_gang_ships']))
    stats['cyno'] = stats['cyno'] / (stats['processed_killmails'] + 0.01)
    stats['capital_use'] = stats['capital_use'] / (stats['processed_killmails'] + 0.01)
    stats['blops_use'] = stats['blops_use'] / (stats['processed_killmails'] + 0.01)
    stats['roleplaying_dock_workers'] = stats['roleplaying_dock_workers'] / (stats['processed_killmails'] + 0.01)
    if stats['blops_use'] > config.BLOPS_HL_PERCENTAGE:
        stats['warning'] = add_string(stats['warning'], 'BLOPS')
    if stats['cyno'] > config.CYNO_HL_PERCENTAGE:
        stats['warning'] = add_string(stats['warning'], 'CYNO')
    if stats['super'] > 0:
        stats['warning'] = add_string(stats['warning'], 'SUPER')
    if stats['titan'] > 0:
        stats['warning'] = add_string(stats['warning'], 'TITAN')
    if stats['roleplaying_dock_workers'] > config.SB_HL_PERCENTAGE:
        stats['warning'] = add_string(stats['warning'], 'SMARTBOMB')
    return stats


def add_string(o, n):
    if o == '':
        return n
    return '{} + {}'.format(o, n)


async def process(data, db):
    """
    :param data: zkill data
    :return: None
    """
    result_killmails = []

    for zkill in data:
        r = db.get_killmail(zkill['killmail_id'])
        if r:
            new_dict = {}
            for k in zkill:
                new_dict[k] = zkill[k]
            for k in r:
                new_dict[k] = r[k]
            result_killmails.append(new_dict)
    data[:] = [z for z in data if z['killmail_id'] not in [d['killmail_id'] for d in result_killmails]]
    Logger.info('Got {} killmails from local cache.'.format(len(result_killmails)))

    if len(data) > 0:
        start_time = time.time()
        async with ClientSession() as session:
            for d in data:
                att = asyncio.ensure_future(fetch(d, session, db))
                result_killmails.append(att)

            results = await asyncio.gather(*result_killmails)
        Logger.info('Gathered {} killmails from CCP servers in {} seconds'.format(len(data), time.time() - start_time))

    """for j in json_results:
        Logger.debug('Parsing {}'.format(j))
        try:
            if not os.path.exists(os.path.join(config.PREF_PATH, 'kills/{}.json'.format(str(j['killmail_id'])))):
                with open(os.path.join(config.PREF_PATH, 'kills/{}.json'.format(str(j['killmail_id']))), 'w') as file:
                    json.dump(j, file)
        except:
            Logger.error('Could not get killmail_id from {}'.format(j))
            json_results.remove(j)"""

    merged_kills = []
    for zkill in data:
        for ccpkill in results:
            if zkill['killmail_id'] == ccpkill['killmail_id']:
                new_dict = {}
                for k in zkill:
                    new_dict[k] = zkill[k]
                for k in ccpkill:
                    new_dict[k] = ccpkill[k]
                merged_kills.append(new_dict)
    return merged_kills


async def fetch(d, session, db):
    """
    :param d:
    :param session:
    :return: json response parsed into dictionary
    """

    """try:
        with open(os.path.join(config.PREF_PATH, 'kills/{}.json'.format(str(d['killmail_id']))), 'r') as json_file:
            return json.load(json_file)
    except:
        pass
        # Logger.info('Failed to open {}.json'.format(str(d['killmail_id'])))"""

    url = "https://esi.evetech.net/v1/killmails/{}/{}/?datasource=tranquility".format(d['killmail_id'], d['zkb']['hash'])
    while True:
        try:
            async with session.get(url) as response:
                r = await response.read()
                s = json.loads(r)
                db.store_killmail(s)
                return s
        except Exception as e:
            Logger.error(e)
            await asyncio.sleep(0.25)


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
