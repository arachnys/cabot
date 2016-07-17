# -*- mode: ruby -*-
# vi: set ft=ruby :
require 'yaml'

# Load local config overrides
local_config = File.file?("local_config.yml") ? YAML.load(File.read("local_config.yml")) : {}

Vagrant::configure("2") do |config|
  # All Vagrant configuration is done here. The most common configuration
  # options are documented and commented below. For a complete reference,
  # please see the online documentation at vagrantup.com.

  # Every Vagrant virtual environment requires a box to build off of.
  config.vm.box = local_config["box"] || "hashicorp/precise64"

  # Virtualbox
  config.vm.provider "virtualbox" do |vb|
    vb.customize [
      "modifyvm", :id,
      "--memory", local_config['ram'] || "1024",
      "--cpus", local_config['cpu'] || 1,
      "--ioapic", "on",
    ]
  end

  #vmware_fusion
  config.vm.provider "vmware_fusion" do |v|
    v.vmx["memsize"] = local_config['ram'] || "1024"
    v.vmx["numvcpus"] = local_config['cpu'] || 1
  end

  # Boot with a GUI so you can see the screen. (Default is headless)
  # config.vm.boot_mode = :gui

  # Assign this VM to a host-only network IP, allowing you to access it
  # via the IP. Host-only networks can talk to the host machine as well as
  # any other machines on the same network, but cannot be accessed (through this
  # network interface) by any external networks.
  config.vm.network "forwarded_port", guest: 5001, host: 5001

  # Share an additional folder to the guest VM. The first argument is
  # an identifier, the second is the path on the guest to mount the
  # folder, and the third is the path on the host to the actual folder.
  config.vm.synced_folder "./", "/vagrant", create: true

  # Provision the development environment
  config.vm.provision :shell do |shell|
    shell.inline = 'sudo /vagrant/bin/provision'
  end
end
