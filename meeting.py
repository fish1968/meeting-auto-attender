#!/usr/bin/env python3
import json
import logging
import openpyxl
import datetime
import time

import platforms

MAX_LATENESS_FOR_MEETING = 600
MEETING_EARLINESS = 60
MAX_COLLECT_DURATION = 15780000   # Seconds in 6 months

logger = logging.getLogger('MEETING')


def log_collected_meetings(src, meetings):
    logger.info('Collected following meetings from {}:'.format(src))
    list(map(logger.info, meetings))


def get_meetings_from_excel():
    meetings = []
    wb = openpyxl.load_workbook('meetings.xlsx')
    sheet = wb['Sheet1']

    for i in sheet.iter_rows(values_only=True):
        if i[0] is not None:
            meetings.append(list(i))
    meetings.pop(0)
    log_collected_meetings("Excel sheet", meetings)
    return meetings


def get_meetings_from_json():
    with open('meetings.json', ) as f:
        meetings = json.load(f)
        log_collected_meetings('JSON', meetings)
        return meetings


def get_meetings():
    meetings = platforms.get_platform().get_meetings_from_outlook() + get_meetings_from_excel() + get_meetings_from_json()
    return meetings


def join_meetings(meetings, automator):
    '''
    :param meetings: List([timestamp, meeting_link, meeting_id, meeting_password, meeting_topic])
    :param automator: automator object implementing 'join_meeting' method
    :return:
    '''
    def convert_time_to_timestamp(meeting):
        meeting[0] = datetime.datetime.strptime(meeting[0], "%d-%m-%Y %H:%M").timestamp()
        return meeting
    meetings = list(map(convert_time_to_timestamp, meetings))
    meetings.sort(key=lambda x: x[0])
    for i, meeting in enumerate(meetings):
        # Setting the meeting times
        current_time = round(time.time(), 0)
        meeting_time = meeting[0]

        # Join sometime early for later scheduled meeting
        if current_time < meeting_time - MEETING_EARLINESS:
            sleep_duration = meeting_time - current_time - MEETING_EARLINESS
            next_meeting_time = datetime.timedelta(seconds=sleep_duration)
            if meeting[1] is not None:
                logger.info('Next bmeeting link: {}'.format(meeting[1]))
            logger.info('Sleeping till the next meeting \"{}\", which is in {}'.format(meeting[4], next_meeting_time))
            time.sleep(sleep_duration)
        # Too much time has passed already
        elif (current_time - meeting_time) > MAX_LATENESS_FOR_MEETING:
            logger.info('Skipped meeting \"{}\" (meeting {}) since more than {} minutes have passed since this '
                        'meeting began '
                  .format(meeting[4], i + 1, MAX_LATENESS_FOR_MEETING / 60))
            continue

        logger.debug(f'Joining meeting with link: {meeting[1]}, id = {meeting[2]}, password = *******')
        automator.join_meeting(meeting_link=meeting[1], meeting_id=meeting[2],
                               meeting_password=meeting[3])

