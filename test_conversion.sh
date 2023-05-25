#!/usr/bin/env bash

#git clone git@github.com:UniversalDependencies/UD_Kyrgyz-KTMU.git
#rm -rf UD_Kyrgyz-KTMU/.git
#python ud2apertium.py

echo "**** Cloning apertium-kir, may take a while..."
git clone git@github.com:apertium/apertium-kir.git

echo "**** Updating the configurations and building..."
cd apertium-kir/ && autoupdate && ./autogen.sh && ./configure && make

echo "**** Testing..."
echo "Бул кыргызча морфологиялык талдоо" | apertium -d . kir-morph

cat ../ky_ktmu-ud.unannotated.txt | apertium -d . kir-morph > ../ky_ktmu-ud.apertium-kir.txt
