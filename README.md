Hi all,

![](http://downloads.indigodomo.com/pluginstore/com.GlennNZ/com.GlennNZ.indigoplugin.irobot/icon.png)

Hopefully not stepping on any toes  :shock: - but have taken FlyingDiver iRoomba plugin (Thanks!) (which is no longer working given firmware changes) and used it as base to rewrite a new Plugin to support the iRoomba mqtt communication protocol.  (as of firmware v.2.2.9-1 29th December 2017).  This was helped a lot by a recent python library for roomba control.

Currently - have it functioning well and it enables a continuous connection to one Roomba-980 or multiple intermittent connections to two or more Roombas (although cannot test that aspect - as only have one sadly)

The benefit of continuous connection is status is updated immediately - so can trigger events to occur which happen within a few seconds; Status is immediately updated.
The library I am using also supports mapping/drawing a map of cleaning - which I would imagine would look good on a control page.  (I haven't worked through those aspects as yet - but have it on a todo list)

Supports:

iRoomba 900 series

iRoomba i7/i7+

iRoomba s9/S9+

***Installation:***

Indigo 7 Only

**Needs paho-mqtt for python installed via terminal window:
Within a terminal Window:
` <sudo> pip install paho-mqtt  `**

Download and Install from Plugin Store as below link:

https://www.indigodomo.com/pluginstore/132/
or
https://github.com/Ghawken/Indigo-iRobotRoomba

***Setup***

For this plugin to work correctly you irobot needs to have a fixed IP address so to know whom it is.   Assign your iroomba a fixed IP address; either a router level (would be my recommendation) or within iroomba setup.

Install the plugin.

*Configure the Plugin:*
![](https://preview.ibb.co/gS30CG/Plugin_Config.png)

[i]Update Device status frequency[/i]:  This is the interval between checks on iroomba status.  Does not apply if running as continuous connection.
[i]Continous connection to ONE Roomba Device only[/i]  Preferred method of communication.  Maintains constant local connection to iroomba.  If any status change any triggers or status change triggers will occur immediately.  Reestablishes the connection only every 24 hours.   If any communication issues restarts the plugin to overcome.

*Create your iroomba Device*
![](https://preview.ibb.co/b99wmb/Device_Irobot.png)

&
Edit Settings

![](https://image.ibb.co/nMD0CG/Configure_IRobot.png)

[i]Roomba IP Address:[/i]  Enter the IP address (fixed ideally) of your iroomba robot

This can be a slightly tricky part as need to be quick between activating iroomba with holding Home button (four notes confirm) and pressing the Get Password button.
Indigo will also give a timeout error (as communication takes longer than allowed).  This can be ignored.
This will possibility take a couple of goes to establish communication.

It then saves the communication password to a IP address based config file and will use this file if you happen to delete you device.


**Status**

The plugin reports the following status - and this is updated live in the setting of continuous communication.

![](https://image.ibb.co/cachRb/Status_Page.png)


**Actions**

The plugin supports the following actions to control you iroomba.

[![](https://image.ibb.co/bwo3zw/irobotactions.png)](https://imgbb.com/)




What could go wrong:

1. Connection fails with a 'Broken Pipe' Error:

Debug info may display the following info about your iroomba during the Get Password connection phase:
    iRobot-Roomba Debug Received: {
    "robotname": "pmgk roomba rdc ",
    "sku": "R980020",
    "nc": 0,
    "ver": "2",
    **"proto": "http",**
    "ip": "192.168.1.13",
    "hostname": "Roomba-",
    **"sw": "v1.6.4", **
    "mac": "
    }

This means that your iroomba is on very old software 1.6.4 and is still using its old http protocol.  The iroomba automatically update when connected to cloud after a short period of time (unless blocked at firewall level).
This plugin only works on the newer firmware version.
Wait it out and your iroomba will be updated and try again.

2. If you do not have a fixed IP address for your device it will lose its connection when this is updated by your dhcp server.  Set it to fixed.

3. Occasionally if the plugin loses its connection to iroomba it will restart the plugin itself to reestablish.  It does this automatically with no user input required.




Glenn
