# vmnet
VM networks for block chain

## Setup

1. Clone vmnet
```
git clone https://github.com/Lamden/vmnet.git
```

1. Install VirtualBox and vargrant
```
brew cask install virtualbox
brew cask install vagrant
```

1. Launch all the VMs
```
vagrant up
```

1. Go into the mgmt VM instance
```
vagrant ssh mgmt
```

1. Allow nodes to talk to each other (ansible uses ssh), password = vagrant
```
vagrant@mgmt:~$ cd /vagrant/playbooks
vagrant@mgmt:/vagrant/playbooks$ ansible-playbook add-key.yml --ask-pass
```

1. Install and configure your nodes
```
vagrant@mgmt:~$ cd /vagrant/playbooks
vagrant@mgmt:/vagrant/playbooks$ ansible-playbook /vagrant/playbooks/configure_nodes.yml
```

## Usage

1. Start witnesses
```
vagrant@mgmt:~$ cd /vagrant/playbooks
vagrant@mgmt:/vagrant/playbooks$ ansible-playbook start-witnesses.yml
```

1. Start master node
```
vagrant@mgmt:~$ cd /vagrant/playbooks
vagrant@mgmt:/vagrant/playbooks$ ansible-playbook start-master.yml
```
