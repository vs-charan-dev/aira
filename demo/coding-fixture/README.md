# AIRA coding demo

A tiny local invoice module with a deliberately incorrect discount calculation. Run `node --test` to see two failing cases. Ask AIRA to investigate, then explicitly ask it to fix invoice.js without changing the tests. The task report records observed test exits and the source diff.

This project has no dependencies, credentials, network calls or deployment. The tracked template is copied to data/projects/aira-demo. Setup never overwrites an existing demo. After a successful fix, invoice.js remains fixed; restore the template manually only when you want another demo.
