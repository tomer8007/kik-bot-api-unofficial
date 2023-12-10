The following message formats are examples of how kik's language (or XMPP elements) actually look like.

This page is useful when you just want to have an idea of what certain events look like in XMPP, or you want to support a type of event which is not implemented yet by the API.

The following events were contributed by: [maritaria](https://github.com/maritaria), [Jaapp](https://github.com/Jaapp-), [LynxKik](https://github.com/LynxKik).

## General ##

Receiving a delivery notification for a sent message:

```xml
<message type="receipt" id="[GUID]" xmlns="jabber:client" to="[BOT_JID]@talk.kik.com" from="[USER_JID]@talk.kik.com">
	<receipt type="delivered" xmlns="kik:message:receipt">
		<msgid id="[MESSAGE_ID]"/>
	</receipt>
	<kik app="chat" push="false" timestamp="1511183559656" qos="true" hop="true"/>
	<g jid="[GROUP_JID]@groups.kik.com"/>
</message>
```

Receiving a read notification for a sent message:

```xml
<message from="[USER_JID]@talk.kik.com" to="[BOT_JID]@talk.kik.com" type="receipt" cts="1511183930239" xmlns="jabber:client" id="[GUID]">
	<kik qos="true" timestamp="1511183930239" push="false" hop="true" app="chat"/>
	<receipt xmlns="kik:message:receipt" type="read">
		<msgid id="[MESSAGE_ID_1]"/>
		<msgid id="[MESSAGE_ID_2]"/>
		<msgid id="[MESSAGE_ID_3]"/>
		<msgid id="[MESSAGE_ID_4]"/><!-- you can receive multiple at a time -->
	</receipt><g jid="[GROUP_JID]@groups.kik.com"/>
</message>
```

Requesting the roster (the groups and people you are chatting with):

```xml
<iq type="get" id="[GUID]">
	<query p="8" xmlns="jabber:iq:roster" />
</iq>
```

Response to requesting roster:

```xml
<iq to="[BOT_JID]@talk.kik.com/CAN167da12427ee4dc4a36b40e8debafc25" type="result" id="[REQUEST_GUID]">
	<query ts="1511180666000" xmlns="jabber:iq:roster">
		<g is-public="true" jid="[GROUP_JID]@groups.kik.com">
			<code>#[GROUP_HASHTAG]</code>
			<n>[GROUP_DISPLAY_NAME]</n>
			<pic ts="1505911808105">http://profilepics.cf.kik.com/[SOME_IDENTIFIER]</pic>
			<m s="1" a="1">[USER_JID]@talk.kik.com</m><!-- owner -->
			<m a="1">[USER_JID]@talk.kik.com</m><!-- admin -->
			<m>[USER_JID]@talk.kik.com</m><!-- user -->
			<!-- users are listed here until the end -->
		</g>
		<!-- all other groups follow the same format and appear before the users are listed -->
		<item jid="kikteam@talk.kik.com">
			<username>kikteam</username>
			<display-name>Kik Team</display-name>
			<pic ts="1479751536620">http://profilepics.cf.kik.com/9wG3zRZW8sLxLnpmyOfwNE7ChYk</pic>
			<verified/><!-- indicates the user has a purple gear -->
			<pubkey/>
		</item>
	</query>
</iq>
```

Removing a friend using their JabberID:

```xml
<iq type="set" id="[GUID]">
	<query xmlns="kik:iq:friend">
		<remove jid="[FRIEND_JID]" />
	</query>
</iq>
```

Response:

```xml
<iq to="[BOT_JID]" id="[GUID_FROM_REQUEST]" type="result">
	<query status="ok" xmlns="kik:iq:friend"/>
</iq>
```
_According to the code the request is succesfull if `status` is equal to `ok`, otherwise it has failed._

## Group messeging ##

When your bot gets added to a group (the bot has chatted with the inviter, so it gets added immediately):

```xml
<message from="[NUMBERS]_g@groups.kik.com" to="mari_bot_3gn@talk.kik.com" type="groupchat" id="[GUID]" xmlns="jabber:client">
    <kik qos="true" app="all" hop="true" timestamp="1510865418472" push="false"/>
    <request d="false" r="false" xmlns="kik:message:receipt"/>
    <roster/>
    <g is-public="true" jid="[NUMBERS]_g@groups.kik.com"><!-- NUMBERS same as message.from -->
        <code>#[PUBLIC_GROUP_HASH]</code>
        <n>Bot testing ground</n>
        <pic ts="1505911808105">http://profilepics.cf.kik.com/[REDACTED]</pic>
        <m>[JID]@talk.kik.com</m><!-- The jid of the bot is also in the list -->
        <m>[JID]@talk.kik.com</m><!-- Some other member -->
        <m s="1" a="1">[JID]@talk.kik.com</m><!-- Owner account, S=owner A=admin -->
    </g>
    <sysmsg xmlns="kik:msg:info">[FIRSTNAME] [LASTNAME] has added you to the chat</sysmsg>
</message>
```

Sending a message in a group:

```xml
<message type="groupchat" to="[GROUP_JID]@groups.kik.com" id="[GUID]" cts="1511183566420"><!-- id is MESSAGE_ID later on -->
	<body>[MESSAGE_TO_SEND]</body>
	<pb></pb>
	<preview></preview><!-- this doesnt matter -->
	<kik push="true" qos="true" timestamp="1511183566420" />
	<request xmlns="kik:message:receipt" r="true" d="true" /><!-- r: receive read request d: receive delivery request -->
	<ri/>
</message>
```

When someone sends a message in a group:

```xml
<message id="[GUID]" type="groupchat" cts="1510911505345" xmlns="kik:groups" from="[USER_JID]@talk.kik.com" to="[BOT_JID]@talk.kik.com">
	<body>Is vervelend... aan de plus kant ik weet nu hoe het eruit ziet als iemand we gaat...</body><!-- This is the original message as captured during the test -->
	<pb/>
	<preview>Is vervele...</preview><!-- some shortened version of the body -->
	<kik timestamp="1510911505345" push="true" app="chat" qos="true" hop="true"/>
	<request d="true" r="true" xmlns="kik:message:receipt"/>
	<ri/>
	<g jid="[GROUP_JID]@groups.kik.com"/><!-- group the message was posted in -->
</message>
```

When someone starts or is typing:

```xml
<message id="[GUID]" type="groupchat" xmlns="kik:groups" from="[TYPING_USER_JID]@talk.kik.com" to="[BOT_JID]@talk.kik.com">
	<pb/>
	<kik timestamp="1510911793198" push="false" app="chat" qos="false" hop="true"/>
	<is-typing val="true"/>
	<g jid="[GROUP_JID]@groups.kik.com"/><!-- the group the user is typing in -->
</message>
```

When someone stops typing:

```xml
<message id="[GUID]" type="groupchat" xmlns="kik:groups" from="[TYPING_USER_JID]@talk.kik.com" to="[BOT_JID]@talk.kik.com">
	<pb/>
	<kik timestamp="1510911793414" push="false" app="chat" qos="false" hop="true"/>
	<is-typing val="false"/>
	<g jid="[GROUP_JID]@groups.kik.com"/>
</message>
```

Receiving an image taken with the kik camera in a group chat:

```xml
<message from="[USER_JID]@talk.kik.com" cts="1511197075873" to="[BOT_JID]@talk.kik.com" id="[GUID]" xmlns="kik:groups" type="groupchat">
	<pb/>
	<kik push="true" hop="true" app="chat" timestamp="1511197075873" qos="true"/>
	<request r="true" xmlns="kik:message:receipt" d="true"/>
	<content app-id="com.kik.ext.camera" id="[GUID]" v="2">
		<strings>
			<app-name>Camera</app-name>
			<file-size>49656</file-size>
			<allow-forward>true</allow-forward>
			<file-content-type>image/jpeg</file-content-type>
			<file-name>[GUID from content#id].jpg</file-name>
			<file-url>https://platform.kik.com/content/files/[GUID from content#id]?t=[KEY]</file-url>
		</strings>
		<extras/>
		<hashes>
			<sha1-original>B00C270632D11ECE461A487052394975A47EAA28</sha1-original>
			<sha1-scaled>E5CDB95540F7ADE7801CA152CC8C33227ABCEA92</sha1-scaled>
			<blockhash-scaled>00000001FFFEFF7F03A0FFFEFFF00000FFFFEFC700030010000F3FFFFC03001F</blockhash-scaled>
		</hashes>
		<images>
			<preview>LARGE_BLOB_OF_DATA</preview>
			<icon>LARGE_BLOB_OF_DATA</icon>
		</images>
		<uris/>
	</content><g jid="[GROUP_JID]@groups.kik.com"/>
</message>
```

Receiving a gallery image in a group chat:

```xml
<message from="[USER_JID]@talk.kik.com" cts="1511197087988" to="[BOT_JID]@talk.kik.com" id="[GUID]" xmlns="kik:groups" type="groupchat">
	<pb/>
	<kik push="true" hop="true" app="chat" timestamp="1511197087988" qos="true"/>
	<request r="true" xmlns="kik:message:receipt" d="true"/>
	<content app-id="com.kik.ext.gallery" id="[GUID]" v="2">
		<strings>
			<app-name>Gallery</app-name>
			<file-size>171087</file-size>
			<allow-forward>true</allow-forward>
			<file-name>[GUID from content#id].jpg</file-name>
			<file-url>https://platform.kik.com/content/files/[GUID from content#id]?t=[KEY]</file-url>
		</strings>
		<extras/>
		<hashes>
			<sha1-scaled>EC3C7C23B00F84010B33754AC7E51FCD26E630A3</sha1-scaled>
			<blockhash-scaled>FFFE00000000FFFF00001F101FFE3FFE1FE00FF807F803F01FFE0FFC07F80040</blockhash-scaled>
			<sha1-original>9AE9130EE3BB5CCC7F8D449B5BD778D4A916BD6C</sha1-original>
		</hashes>
		<images>
			<preview>LARGE_BLOB_OF_DATA</preview>
			<icon>LARGE_BLOB_OF_DATA</icon>
		</images>
		<uris/>
	</content><g jid="[GROUP_JID]@groups.kik.com"/>
</message>
```
_Note: the image urls can be opened in a browser without further authentication_

Receiving a sticker (in a group chat):

```xml
<message cts="1511347191450" id="[GUID]" xmlns="kik:groups" to="[BOT_JID]" from="[USER_JID]" type="groupchat">
	<pb/>
	<kik qos="true" hop="true" timestamp="1511347191450" app="chat" push="true"/>
	<request d="true" r="true" xmlns="kik:message:receipt"/>
	<content v="2" app-id="com.kik.ext.stickers" id="dbffd5eb-3f4d-43d8-b240-2ad0379e9ec1">
		<strings>
			<app-name>Stickers</app-name>
			<attribution/>
			<layout>photo</layout>
			<video-should-loop>false</video-should-loop>
			<video-should-autoplay>false</video-should-autoplay>
			<disallow-save>false</disallow-save>
			<video-should-be-muted>false</video-should-be-muted>
			<title/>
			<text/>
			<allow-forward>false</allow-forward>
		</strings>
		<extras>
			<item>
				<key>sticker_pack_id</key>
				<val>cosmocat</val>
			</item>
			<item>
				<key>sticker_url</key>
				<val>https://cdn.kik.com/stickersv2/packs/cosmocat/05.png</val>
			</item>
			<item>
				<key>sticker_id</key>
				<val>5946604915261440</val>
			</item>
			<item>
				<key>sticker_source</key>
				<val>Pack</val>
			</item>
		</extras>
		<hashes/>
		<images>
			<png-preview>BASE64_BLOB</png-preview>
		</images>
		<uris>
			<uri platform="com.kik.ext.stickers">https://stickers.kik.com/</uri>
			<uri platform="cards">https://stickers.kik.com/</uri>
		</uris>
	</content>
	<g jid="[GROUP_JID]"/>
</message>
```

Receiving a message from a bot with an embedded keyboard (reply label below the message bubble):

```xml
<!-- someone summoning the bot-->
<message cts="1511347420147" id="[GUID]" xmlns="kik:groups" to="[YOUR_BOT_JID]" from="[USER_JID]" type="groupchat">
	<body>@whoslurking Who's lurking? (10 secs)</body>
	<mention>
		<bot>whoslurking_ii6@talk.kik.com</bot>
	</mention>
	<pb>[BASE64_BLOB]</pb>
	<preview>@whoslurki...</preview>
	<kik qos="true" hop="true" timestamp="1511347420147" app="chat" push="true"/>
	<request d="true" r="true" xmlns="kik:message:receipt"/>
	<g jid="[GROUP_JID]"/>
</message>
<!-- bot reply -->
<message cts="1511347420713" id="[GUID]" xmlns="jabber:client" to="[YOUR_BOT_JID]" from="whoslurking_ii6@talk.kik.com" type="groupchat">
	<kik qos="true" hop="true" timestamp="1511347420713" app="chat" push="true"/>
	<request d="true" r="true" xmlns="kik:message:receipt"/>
	<body>Calculating who's lurking... please click get results in a 10 seconds!</body>
	<g jid="[GROUP_JID]"/>
	<pb>BASE64_BLOB</pb>
	<suggested-responses hidden="false">
		<text>Who&apos;s lurking? (10 secs)</text>
		<text>Who&apos;s lurking? (30 secs)</text>
		<text>Who&apos;s lurking? (60 secs)</text>
		<text>Get results</text>
		<text>Help</text>
	</suggested-responses>
</message>
```

When someone leaves a (public) group your bot is a member of:

```xml
<message type="groupchat" xmlns="jabber:client" id="[GUID]" from="[NUMBERS]_g@groups.kik.com" to="[BOT_JID]@talk.kik.com"><!-- JID of group -->
	<kik timestamp="1510911460608" push="false" app="all" qos="true" hop="true"/>
	<request d="false" r="false" xmlns="kik:message:receipt"/>
	<roster/>
	<g jid="[NUMBERS]_g@groups.kik.com"> <!-- JID of group -->
		<l>[USER_JID]@talk.kik.com</l><!-- JID of user that left -->
	</g>
	<status jid="[USER_JID]@talk.kik.com">[FIRSTNAME] [LASTNAME] has left the chat</status>
</message>
```

## History Retrieval ##

These are the messages for obtaining history. It happens in a loop.

1. This request is sent
```xml
<iq type="set" id="[GUID]" cts="1513349802685">
    <query xmlns="kik:iq:QoS">
	<msg-acks />
	<history attach="true" />
    </query>
</iq>
```

2. Within the "history" tag regular messages are sent with "msg" tags (those are "message" tags in our current parsing code).
```xml
<iq type="result" id="[GUID]" from="warehouse@talk.kik.com" to="[USER_JID]@talk.kik.com/...">
    <query xmlns="kik:iq:QoS">
	<history more="1" attach="true">
	    <msg type="receipt" id="[MESSAGE_ID]" from="lemagedurage_52o@talk.kik.com">
		<kik app="chat" push="false" timestamp="1511036055842" qos="true"/>
		<receipt type="read" xmlns="kik:message:receipt">
		    <msgid id="[MESSAGE_ID]"/>
		</receipt>
	    </msg>
	    <msg type="chat" id="[GUID]" from="[USER_JID]@talk.kik.com">
		<body>Hi</body>
		<pb/>
		<preview>Hi</preview>
		<kik app="chat" push="true" timestamp="1511036150972" qos="true"/>
		<request d="true" xmlns="kik:message:receipt" r="true"/>
		<ri/>
	    </msg>
	    <msg type="groupchat" id="[GUID]" from="[USER_JID]@talk.kik.com">
		<body>Uhh</body>
		<pb/>
		<preview>Uhh</preview>
		<kik app="chat" push="true" timestamp="1511036907685" qos="true"/>
		<request d="true" xmlns="kik:message:receipt" r="true"/>
		<ri/>
		<g jid="[GROUP_JID]_g@groups.kik.com"/>
	    </msg>
	</history>
	<polling interval="60"/>
    </query>
</iq>
```
3. When calling the first request again, the same response is sent. To get the next chunk of history, acks are sent for each message of the last chunk, along with the new history request.
```xml
<iq type="set" id="[GUID]" cts="1513349804653">
    <query xmlns="kik:iq:QoS">
	<msg-acks>
	    <sender jid="[USER_JID]@talk.kik.com">
		<ack-id receipt="false">[MESSAGE_ID]</ack-id>
		<ack-id receipt="true">[MESSAGE_ID]</ack-id>
	    </sender>
	    <sender jid="[USER_JID]@talk.kik.com"  g="[GROUP_JID]_g@groups.kik.com">
		<ack-id receipt="false">[MESSAGE_ID]</ack-id>
		<ack-id receipt="true">[MESSAGE_ID]</ack-id>
	    </sender>
	</msg-acks>
	<history attach="true" />
    </query>
</iq>
```

## Group adminship ##

Add people to a group:

```xml
<iq type="set" id="[GUID]">
    <query xmlns="kik:groups:admin">
	<g jid="[GUID]">
	    <m>[USER_JID_1]@talk.kik.com</m>
            <m>[USER_JID_2]@talk.kik.com</m>
	</g>
    </query>
</iq>
```

Remove someone from group:

```xml
<iq type="set" id="[GUID]">
    <query xmlns="kik:groups:admin">
	<g jid="[GUID]">
	    <m r="1">[USER_JID]@talk.kik.com</m>
	</g>
    </query>
</iq>
```
Change the group name:

```xml
<iq type="set" id="[GUID]">
    <query xmlns="kik:groups:admin">
	<g jid="[GUID]">
	    <n>[GROUPNAME]</n>
	</g>
    </query>
</iq>
```

Ban:

```xml
<iq type="set" id="[GUID]">
    <query xmlns="kik:groups:admin">
	<g jid="[GUID]">
	    <b>[USER_JID]@talk.kik.com</b>
	</g>
    </query>
</iq>
```

Unban:

```xml
<iq type="set" id="[GUID]">
    <query xmlns="kik:groups:admin">
	<g jid="[GUID]">
	    <b r="1">[USER_JID]@talk.kik.com</b>
	</g>
    </query>
</iq>
```

_Banned members are listed with \<b\>[JID]\</b\> instead of \<m\>._

Notification message when another admin has unbanned a member:

```xml
<message id="[GUID]" to="[BOT_JID]" type="groupchat" xmlns="jabber:client" from="[GROUP_JID]">
	<kik qos="true" timestamp="1511359715596" app="all" push="false" hop="true"/>
	<request r="false" d="false" xmlns="kik:message:receipt"/>
	<roster/>
	<g jid="[GROUP_JID]"/>
	<status jid="[UNBANNED_USER_JID]">[FIRSTNAME] [LASTNAME] has unbanned [FIRSTNAME]
 [LASTNAME]</status>
</message>
```

When someone makes you admin:

```xml
<message type="groupchat" to="[BOT_JID]@talk.kik.com" xmlns="jabber:client" id="[GUID]" from="[GROUP_JID]@groups.kik.com">
	<kik hop="true" push="false" app="all" qos="true" timestamp="1511180642944"/>
	<request d="false" r="false" xmlns="kik:message:receipt"/>
	<roster/>
	<g jid="[GROUP_JID]@groups.kik.com"/>
	<sysmsg xmlns="kik:msg:info">You have been promoted to admin by [ADMIN_FIRSTNAME] [ADMIN_LASTNAME]</sysmsg>
</message>
```

When the owner of a group removes your adminship:

```xml
<message type="groupchat" to="[BOT_JID]@talk.kik.com" xmlns="jabber:client" id="[GUID]" from="[GROUP_JID]@groups.kik.com">
	<kik hop="true" push="false" app="all" qos="true" timestamp="1511180665857"/>
	<request d="false" r="false" xmlns="kik:message:receipt"/>
	<roster/>
	<g jid="[GROUP_JID]@groups.kik.com"/>
	<sysmsg xmlns="kik:msg:info">Your admin status has been removed by [ADMIN_FIRSTNAME] [ADMIN_LASTNAME]</sysmsg>
</message>
```

Request to make another member an admin:

```xml
<iq type="set" id="[GUID]">
	<query xmlns="kik:groups:admin">
		<g jid="[GROUP_JID]">
			<m a="1">[USER_JID]</m>
		</g>
	</query>
</iq>

```

Response when the bot is an admin and the target user is in the group:

```xml
<iq to="[BOT_JID]" type="result" id="[GUID]">
	<query xmlns="kik:groups:admin"/>
</iq>
```
_The request also succeeds if the user is already an admin_

Response when the bot is not an admin:

```xml
<iq to="[BOT_JID]" type="error" id="[GUID]">
	<query xmlns="kik:groups:admin"><!-- the server echo's back the request as well -->
		<g jid="[GROUP_JID]">
			<m a="1">[TARGET_USER_JID]</m>
		</g>
	</query>
	<error type="modify" code="400">
		<bad-request xmlns="urn:ietf:params:xml:ns:xmpp-stanzas"/>
		<not-admin/>
	</error>
</iq>
```
_According to the code the request has succeded if one of the following nodes are *not* present in the response before reaching the closing `</iq>`:_ `<not-authorized/>` (_The bot is not authorized_), `<not-member/>` _(The target member is not in the group)_, `<bad-request/>`

Request to remove admin privileges from (demote) someone:

```xml
<iq type="set" id="[GUID]">
    <query xmlns="kik:groups:admin">
	<g jid="[GUID]">
	    <m a="0">[USER_JID]@talk.kik.com</m>
	</g>
    </query>
</iq>
```

## Registration ##

Validating first/last name when registering:
```xml
<iq type="get" id="[GUID]">
    <query xmlns="kik:iq:check-unique">
	<first>[FIRST_NAME]</first>
	<last>[LAST_NAME]</last>
    </query>
</iq>
```

Response for validating first/last name:
```xml
<iq id="[GUID]" type="result">
    <query xmlns="kik:iq:check-unique">
	<first is-valid="[GUID]">[FIRST_NAME]</first>
	<last is-valid="[GUID]">[LAST_NAME]</last>
    </query>
</iq>
```

Validating username:

```xml
<iq type="get" id="[GUID]">
    <query xmlns="kik:iq:check-unique">
	<username>[USER_NAME]</username>
    </query>
</iq>
````
Response for validating username:

```xml
<iq id="[GUID]" type="result">
    <query xmlns="kik:iq:check-unique">
	<username is-unique="false">[USER_NAME]</username>
    </query>
</iq>
```

Registering an account without captcha:

```xml
<iq type="set" id="[GUID]">
    <query xmlns="jabber:iq:register">
	<email>[EMAIL]</email>
	<passkey-e>[PASSKEY_E]</passkey-e>
	<passkey-u>[PASSKEY_U]</passkey-u>
	<device-id>[DEVICE_ID]</device-id>
	<username>[USERNAME]</username>
	<first>[FIRST_NAME]</first>
	<last>[LAST_NAME]</last>
	<birthday>1974-11-20</birthday>
	<version>11.38.0.18991</version>
	<device-type>android</device-type>
	<model>Nexus 7</model>
	<android-sdk>25</android-sdk>
	<registrations-since-install>1</registrations-since-install>
	<install-date>unknown</install-date>
	<logins-since-install>0</logins-since-install>
	<prefix>CAN</prefix>
	<lang>en_US</lang>
	<brand>google</brand>
	<android-id>[ANDROID_ID]</android-id>
    </query>
</iq>
```

Response for registering an account without captcha:
```xml
<iq id="[GUID]" type="error">
    <query xmlns="jabber:iq:register">
	<email>[EMAIL]</email>
	<passkey-e>[PASSKEY_E]</passkey-e>
	<passkey-u>[PASSKEY_U]</passkey-u>
	<device-id>[DEVICE_ID]</device-id>
	<username>[USERNAME]</username>
	<first>[FIRST_NAME]</first>
	<last>[LAST_NAME]</last>
	<birthday>1974-11-20</birthday>
	<version>11.38.0.18991</version>
	<device-type>android</device-type>
	<model>Nexus 7</model>
	<android-sdk>25</android-sdk>
	<registrations-since-install>1</registrations-since-install>
	<install-date>unknown</install-date>
	<logins-since-install>0</logins-since-install>
	<prefix>CAN</prefix>
	<lang>en_US</lang>
	<brand>google</brand>
	<android-id>[ANDROID_ID]</android-id>
    </query>
    <error code="406" type="modify">
	<not-acceptable xmlns="urn:ietf:params:xml:ns:xmpp-stanzas"/>
	<challenge xmlns="kik:challenge">
	    <captcha-type>web</captcha-type>
	    <captcha-url>https://captcha.kik.com/?id=3-CAISiQH3dSVnHFxSCTcxpLm6xpIRal28c1ZY7O4sL7QEzbr4qicZMlZ3CNTEZchgi2y7SrD5Dx2HEv7-aAUAI7D3sghKUJVMFa40sahnwmPjbfFtn6JdC2tafixYgBgbsgW706uImDJTqpULUUEJOS-IevcGpiC1PazXFiU6udk_rIPX2wR0DPKsZifoGRoQ8NibGHt7-xa-kdZDonatbyIfofH3geWQWZq31WeeQzP2ykl_uxBRbdLxNKx7g8ewcioQW9biyUFQ1aWnADmF9V1_TQ&amp;lang=en&amp;is_native=false</captcha-url>
	    <captcha-challenge-id>3-CAISiQH3dSVnHFxSCTcxpLm6xpIRal28c1ZY7O4sL7QEzbr4qicZMlZ3CNTEZchgi2y7SrD5Dx2HEv7-aAUAI7D3sghKUJVMFa40sahnwmPjbfFtn6JdC2tafixYgBgbsgW706uImDJTqpULUUEJOS-IevcGpiC1PazXFiU6udk_rIPX2wR0DPKsZifoGRoQ8NibGHt7-xa-kdZDonatbyIfofH3geWQWZq31WeeQzP2ykl_uxBRbdLxNKx7g8ewcioQW9biyUFQ1aWnADmF9V1_TQ</captcha-challenge-id>
	</challenge>
    </error>
</iq>
```

Registering an account with filled-in captcha:

```xml
<iq type="set" id="[GUID]">
    <query xmlns="jabber:iq:register">
	<email>[EMAIL]</email>
	<passkey-e>[PASSKEY_E]</passkey-e>
	<passkey-u>[PASSKEY_U]</passkey-u>
	<device-id>[DEVICE_ID]</device-id>
	<username>[USERNAME]</username>
	<first>[FIRST_NAME]</first>
	<last>[LAST_NAME]</last>
	<birthday>1974-11-20</birthday>
	<challenge>
	    <response>eyJraWQiOiI4YTNiZWM2N2IwN2I0MjcxMmMxMDI1YTJhZDJjZDcwYjk5ZGI4MTQ4IiwiY3R5IjoidGV4dFwvcGxhaW4iLCJhbGciOiJSUzI1NiJ9.My1DQUlTaVFIM2RTVm5IRnhTQ1RjeHBMbTZ4cElSYWwyOGMxWlk3TzRzTDdRRXpicjRxaWNaTWxaM0NOVEVaY2hnaTJ5N1NyRDVEeDJIRXY3LWFBVUFJN0Qzc2doS1VKVk1GYTQwc2FobndtUGpiZkZ0bjZKZEMydGFmaXhZZ0JnYnNnVzcwNnVJbURKVHFwVUxVVUVKT1MtSWV2Y0dwaUMxUGF6WEZpVTZ1ZGtfcklQWDJ3UjBEUEtzWmlmb0dSb1E4TmliR0h0Ny14YS1rZFpEb25hdGJ5SWZvZkgzZ2VXUVdacTMxV2VlUXpQMnlrbF91eEJSYmRMeE5LeDdnOGV3Y2lvUVc5Yml5VUZRMWFXbkFEbUY5VjFfVFE.i0uIxt8---IddaR_y9cGqYm977IcvrSV-m3VPQv_Ape4OF5HY_FwuWBcZUdmUy4UwhZSQhIi5zmwpF6k9UnOgAeQg2QQUfXFXH-L5bChKCd-vrZ2r-V-cv0i6B1e74omAn5t8xxtDgjvJFrRr0qYY6hLxTM2E1fwqzjfjdC9ijM1wnI3jw7sE-on2Kc6OEW6kCgiFcbpurC8Gz7AxDhIybHqnKNOdhiPZalw0peFbEIKa9NLDRT2xEjmM2elkhyJ7re5jGS9u_nyQxjILYjFR1bVcdtHwkOAUzMpMKEGJANMztswLZy4ElNergP4O0pc6hS-4-fApjsacaO-Ew_M6Q</response>
	</challenge>
	<version>11.38.0.18991</version>
	<device-type>android</device-type>
	<model>Nexus 7</model>
	<android-sdk>25</android-sdk>
	<registrations-since-install>1</registrations-since-install>
	<install-date>unknown</install-date>
	<logins-since-install>0</logins-since-install>
	<prefix>CAN</prefix>
	<lang>en_US</lang>
	<brand>google</brand>
	<android-id>[ANDROID_ID]</android-id>
    </query>
</iq>
```

Response for registering an account with captcha:

```xml
<iq id="[GUID]" type="result">
    <query xmlns="jabber:iq:register">
	<node>[USERNAME]_53w</node>
	<xiphias>
	    <response method="GetParticipatingExperiments" service="mobile.abtesting.v1.AbTesting">
		<body>ChkKEWtpbl93YWxsZXRfaXBob25lEgRzaG93ChoKEmtpbl93YWxsZXRfYW5kcm9pZBIEc2hvdwoYCg1naWZfZmF2b3JpdGVzEgdjb250cm9sCh0KE2dyb3VwX2FkZF9wbGFjZW1lbnQSBmJvdHRvbQohChlzZW5kX2dyb3VwX2ludml0ZV9pbl9jaGF0EgRzaG93CiIKD211bHRpcGxlX3Bob3RvcxIPbXVsdGlwbGVfcGhvdG9zCh0KEmJvdC1yZXBseWJ1dHRvbi1VSRIHY29udHJvbAonCh9ib3RfY29udGVudF9tZXNzYWdlX2F0dHJpYnV0aW9uEgRzaG93CiAKFHNyLWtleWJvYXJkLWljb24taW9zEgh0b29sLXRpcAokChx0ZXh0X3dpZGdldF90aWN0YWN0b2Vib3RfaW9zEgRzaG93Ch8KFHB1c2hub3RpZl92aWRlb19jaGF0Egdjb250cm9sChYKDnZvaWNlX21lc3NhZ2VzEgRzaG93ChcKD3BnX3Nob3dfaW5fcGx1cxIEc2hvdwoYChBoYXNodGFnc19iYWRnaW5nEgRzaG93Ch8KF3B1YmxpY2dyb3Vwc19oZWxwZXJfaW9zEgRzaG93ChcKDHByb2ZpbGUtYmlvcxIHY29udHJvbAohChZwcm9maWxlX3RoZW1lc19hbmRyb2lkEgdjb250cm9sCi8KJGVtb2ppLXN0YXR1cy1wcm9maWxlLXBpY3R1cmUtcmVsZWFzZRIHY29udHJvbApACihzZXR0aW5nc19waG90b3ByZXZpZXdfZWZmZWN0c2FuZGNhcHRpb25zEhRmaWx0ZXJzX2FuZF9jYXB0aW9ucwoeChZzdWdnZXN0ZWQtY2hhdHMtaXBob25lEgRzaG93ChMKC3F1aWNrX3JlcGx5EgRzaG93ChoKEG5ld19raWtfZGVmYXVsdHMSBmVuYWJsZQouCiNuZXdfcGVvcGxlX25vdGlmaWNhdGlvbl9zZXR0aW5nX2JhchIHZW5hYmxlZAogChhzaGFyZV9ncm91cF9saW5rc19pcGhvbmUSBHNob3cKIwoRc2hhcmVfZ3JvdXBfbGlua3MSDnBpY3R1cmVfYnV0dG9uChgKEHByaXZhY3lfc2V0dGluZ3MSBHNob3cKJQoaZW5oYW5jZWRfZ2lmX3RhYl8yX2FuZHJvaWQSB2NvbnRyb2wKHwoSbmV0d29ya19lbmNyeXB0aW9uEglmb3JjZV9zc2wKHwoVYmFuLW5vbi1ncm91cC1tZW1iZXJzEgZiYW4tZW0KLAobYmV0dGVyX3B1c2hfb3B0aW5fcmVtaW5kZXJzEg1sb3dfZnJlcXVlbmN5Ch0KFXNjcmliYmxlX2NoYXRfcmVsZWFzZRIEc2hvdwoaChJ2aWRlb2NoYXRfc3RpY2tlcnMSBHNob3cKGgoLZnVsbF9zY3JlZW4SC2Z1bGxfc2NyZWVuChcKD3N1Z2dlc3RlZC1jaGF0cxIEc2hvdwoXCgxnaWYtY2FtZXJhLTISB2NvbnRyb2wKHAoMZWZmZWN0c19oaW50EgxlZmZlY3RzX2hpbnQKJgoRcmVtb3ZlX21pcnJvcmxlc3MSEXJlbW92ZV9taXJyb3JsZXNzCi4KJXZpZGVvX2NoYXRfbm90aWZpY2F0aW9uX3NvdW5kX2FuZHJvaWQSBXNvdW5kCi0KJHZpZGVvX2NoYXRfbm90aWZpY2F0aW9uX3NvdW5kX2lwaG9uZRIFc291bmQKJQoWdGFwX3RvX3ZpZGVvY2hhdF9oaW50cxILYWN0aXZlX2hpbnQKIQoZbmF0aXZlX3N0aWNrZXJzX2lwaG9uZV92MhIEc2hvdwofChduYXRpdmVfc3RpY2tlcnNfYW5kcm9pZBIEc2hvdwohChlmdWxsc2NyZWVuX2NhbWVyYV9hbmRyb2lkEgRzaG93ChsKE2dpZl9zZWFyY2hfYWxsX3RhYnMSBHNob3cKFwoPaGFzaHRhZ3NfcmV0dXJuEgRzaG93Ch4KFmhhc2h0YWdzX3JldHVybl9pcGhvbmUSBHNob3cKHAoRcGVyc2lzdF9jaGF0X2xpc3QSB3BlcnNpc3QKGQoPdW5ibHVyX25ld19jaGF0EgZ1bmJsdXIKMworaW5saW5lX2ludml0ZV9mcmllbmRfdmlhX3VzZV9waG9uZV9jb250YWN0cxIEc2hvdwosCiBkaXNhYmxlX3JlYWRfcmVjZWlwdHNfbmV3X3Blb3BsZRIIZGlzYWJsZWQKFQoNbmV3X2NoYXRzX2JhchIEc2hvdwocChRsYXJnZV9wcm9maWxlX2hlYWRlchIEc2hvdwoZChFmdWxsc2NyZWVuX2NhbWVyYRIEc2hvdwoaChJlbmhhbmNlZF9naWZfdGFiXzISBHNob3cKKAogYWJtX3VwbG9hZF9jb250YWN0c19vbl9vcHRfb3V0XzMSBHNob3cKEwoLZ3Jhbl9yZXBvcnQSBHNob3cKHAoUZ3JhbnVsYXJfcmVwb3J0X3NwYW0SBHNob3cKGQoRa2lsbF9pbWFnZV9zZWFyY2gSBGhpZGUKIQoZa2lsbF9pbWFnZV9zZWFyY2hfYW5kcm9pZBIEaGlkZQoXCg9hYm1fZmluZF9wZW9wbGUSBHNob3cKIQoZYWJtX2J1dHRvbl9tb3ZlX3RvX3RhbGt0bxIEc2hvdwofChVhYm1fcmVnaXN0cmF0aW9uX2Zsb3cSBnNjcmVlbgocChRlbmFibGVfYm90c19mZWF0dXJlcxIEc2hvdwodChV0YWxrX3RvX2lubGluZV90cmF5XzISBHNob3cKHgoWb3B0X2luX3ZpYV9jaGF0X2xpc3RfMhIEc2hvdwofChdoaWRlX2Nvbm5lY3Rpbmdfc3Bpbm5lchIEaGlkZQodChJiYWNrZ3JvdW5kX3JlZnJlc2gSB2VuYWJsZWQKJAoSYWJtX29wdF9vdXRfYnV0dG9uEg50b3BfcmlnaHRfZ3JleQodChVtdXRlX25ld19jaGF0c19idXR0b24SBHNob3cKKwogY2hhdHNjcmVlbl9yYXRpbmdzYnViYmxlX2FuZHJvaWQSB2NvbnRyb2wKGwoQbmV3X3RvX2tpa19iYWRnZRIHY29udHJvbAoiChdtZXNzYWdlX2JhdGNoX2NvdW50X2lvcxIHY29udHJvbAotCiVhYm1fdXBsb2FkX2NvbnRhY3RzX29uX29wdF9vdXRfZGFtbml0EgRzaG93CiEKG25ldHdvcmtfaW50ZXJmYWNlX3NlbGVjdGlvbhICb3MKHQoWc2hvdWxkX2Fsd2F5c19zZWVfdGhpcxIDYWxsCicKFmxlZ2FjeV9oYXNoX2V4cGVyaW1lbnQSDXNlY29uZFZhcmlhbnQKJgoVdmVydXNfaGFzaF9leHBlcmltZW50Eg1zZWNvbmRWYXJpYW50Cg4KCGFfYV90ZXN0EgJhMRAB</body>
	    </response>
	</xiphias>
    </query>
</iq>
```
