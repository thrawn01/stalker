Initial Line by line port to Go AND migration to rethinkdb

- not yet thorougly tested
- see TODO for ...TODO's
- lots of stuff still hard coded


### General prereqs

1. You need a working rethinkdb install
2. You need a working redis install

### Prereqs for building

1. You need a working go install
2. You need godep:

    go get github.com/tools/godep

### Get the go stuff

    git clone https://github.com/pandemicsyn/stalker.git $GOPATH/src/github.com/pandemicsyn/stalker
    cd $GOPATH/src/github.com/pandemicsyn/stalker
    git checkout go
    cd go

### Manually build/install

    godep go install ./...
    mkdir -p /etc/stalker/ && cp -av packaging/root/etc/stalker/stalkerd.toml /etc/stalker
    $GOPATH/bin/stalkerd 

### Or with the make file

    make build

### Or build .deb's

    make packages

