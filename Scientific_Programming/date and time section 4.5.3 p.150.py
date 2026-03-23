import datetime

birthday=datetime.date (1961,6,27)

# Windows does not always support %-d in strftime, so use birthday.day directly
# for the day number and strftime for the other parts.
print(f"my birthday is {birthday.strftime('%A')} {birthday.day}-{birthday.strftime('%b-%Y')}")


# Pure strftime version (may not work the same on Windows because %-d is not always supported)
# the line below fails on my windows pc.
# print(f"my birthday is {birthday.strftime('%A %-d-%b-%Y')}")


lunchtime = datetime.time(13,30)
print(f"Lunchtime is {lunchtime}")

now = datetime.datetime.now()
print(
    f"Current date and time to the millisecond: "
    f"{now.strftime('%A %d-%b-%Y %H:%M:%S')}.{now.microsecond // 1000:03d}"
)
