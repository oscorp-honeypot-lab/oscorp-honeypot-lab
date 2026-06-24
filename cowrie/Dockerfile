FROM cowrie/cowrie:3.0.0@sha256:f5ee0f7d0171cb5d924ae9a96eeb7a3fef876f0217b4052ea22dc3f779691ebe

USER root

COPY --chown=cowrie:cowrie cowrie/patches/network.py /cowrie/cowrie-git/src/cowrie/core/network.py

USER cowrie
