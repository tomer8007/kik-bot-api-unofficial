# Kik Messenger Protobuf API #
[Protocol Buffers](https://developers.google.com/protocol-buffers/) in kik are used for a variety of purposes, for example [searching for groups](https://github.com/tomer8007/kik-bot-api-unofficial/blob/new/kik_unofficial/datatypes/xmpp/roster.py#L127). 
Usually you can identify protobuf services if the `xmlns` field starts with `kik:iq:xiphias:`.

This directory contains most of kik's protobuf datatypes in both source (`.proto` files) and compiled python versions.


## Organization ##
The source files are stored in the `probuf_source` directory. Other directories contain the auto-generated python classes.

An additional bash script `compile_protobuf.sh` in this directory is provided to automaticlly compile new extracted `.proto` files from the Android `apk` file.
