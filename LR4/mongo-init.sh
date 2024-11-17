set -e

mongo <<EOF
db = db.getSiblingDB('arch')
db.orders.createIndex({"id_user": -1}) 
EOF