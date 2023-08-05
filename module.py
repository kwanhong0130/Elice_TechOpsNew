from datetime import datetime, timezone, timedelta

from loguru import logger

def convert_ts_datetime(from_date, from_time):
    # convert begin/end datetime
    to_update_datatime = (from_date, from_time)
    logger.info(to_update_datatime)

    y_str = datetime.strftime(to_update_datatime[0], '%Y')
    m_str = datetime.strftime(to_update_datatime[0], '%m')
    d_str = datetime.strftime(to_update_datatime[0], '%d')

    to_change_date_str = y_str+'/'+m_str+'/'+d_str
    to_chagnge_datetime_str = to_change_date_str + ' ' + from_time

    date_format = '%Y/%m/%d %H:%M:%S'

    # Convert date string to datetime object in GMT+9 timezone
    from_datetime_obj = datetime.strptime(to_chagnge_datetime_str, date_format).replace(tzinfo=timezone(timedelta(hours=9)))

    # Convert datetime object to Unix timestamp in milliseconds
    to_change_ts_datetime = int(from_datetime_obj.timestamp() * 1000)
    logger.info("To change ts_datetime timestamp " + str(to_change_ts_datetime))

    return to_change_ts_datetime