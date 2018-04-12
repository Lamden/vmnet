#!/usr/bin/env bash

# install ansible (http://docs.ansible.com/intro_installation.html)
apt-get -y install software-properties-common
apt-add-repository -y ppa:ansible/ansible
apt-get update
apt-get -y install ansible

# Copy files
#cp -a /vagrant/* /home/vagrant/
#chown -R vagrant:vagrant /home/vagrant

# configure hosts file for our internal network defined by Vagrantfile
cat >> /etc/hosts <<EOL

# vagrant environment nodes
10.0.15.10  mgmt
10.0.15.20  node0
10.0.15.21  node1
10.0.15.22  node2
10.0.15.23  node3
10.0.15.24  node4
10.0.15.25  node5
10.0.15.26  node6
10.0.15.27  node7
10.0.15.28  node8
EOL

echo -e  'y\n' | ssh-keygen -t rsa -b 2048 -N "" -f /home/vagrant/.ssh/id_rsa
ssh-keyscan node0 node1 node2 node3 node4 node5 node6 node7 node8 >> .ssh/known_hosts

