#!/usr/bin/env bash
LIB_V=${LIB_VERSION:-v0}
charmcraft publish-lib "charms.signals.$LIB_V.signals"  # $ TEMPLATE: Filled in by ./scripts/init.sh
