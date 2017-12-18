Hi all,

Roomba 980 Plugin for Indigodomo (Indigodomo.com)

Hopefully not stepping on any toes :shock: - but have taken FlyingDiver iRoomba plugin (Thanks!) (which is no longer working given firmware changes) and used it as base to rewrite a new Plugin to support the iRoomba mqtt communication protocol. (as of firmware v.2.2.9-1 20th May 2017). This was helped a lot by a recent python library for roomba control.

Currently - have it functioning well and it enables a continuous connection to one Roomba-980 or multiple intermittent connections to two or more Roombas (although cannot test that aspect - as only have one sadly)

The benefit of continuous connection is status is updated immediately - so can trigger events to occur which happen within a few seconds; Status is immediately updated.
The library I am using also supports mapping/drawing a map of cleaning - which I would imagine would look good on a control page. (I haven't worked through those aspects as yet - but have it on a todo list)

Have it running for longer (currently 48 hours without connection issue) and bug testing, also slowly adding further items pulled from the mqtt iroomba stream - but those brave can take a leap here:

Usage:

Download and install

Needs paho-mqtt python library installed.
In terminal Window
pip install paho-mqtt

v.0.1.8
Fix for no Internet connection


V.0.0.8

Better checks to allow continuous connection for weeks
Change to logging/less verbose
Add X/Y to devices

v.0.0.5

Supports continuous connection (most tested currently) to one iRoomba or intermittent to multiple
Supports Actions Stop/Start/Pause/Dock sent immediately with continuous connection, or within 15 seconds with intermittent connection.
Status updates immediate (with continuous and more information) or as set in time-interval with intermittent
Saves config details to file in Documents/Indigo-iRoomba for each IP address of Roomba
(can delete, recreate devices and will use same config/password for same IP address)
Get Password from Config Page - works and pulls/saves password (some tidying up of messaging needed)
Enable/Disable Debug mqtt communication as very verbose (and otherwise Indigo would save all to debug log)

Glenn
