import datetime

def get_uptime(launch_time):
    delta = datetime.datetime.now(datetime.timezone.utc) - launch_time
    hours, remainder = divmod(int(delta.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}h {minutes}m {seconds}s"
