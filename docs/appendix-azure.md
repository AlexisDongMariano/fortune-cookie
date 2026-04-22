# Appendix — Azure Equivalent (Chapters 05 + 07)

> **Use this if you prefer Azure over AWS.** Azure is the #2 cloud in job postings, so knowing both is a plus.
> Chapters **06 (Ansible), 08 (Docker), 09 (Observability), 10 (K8s)** are cloud-agnostic — use them as-is.
> Only the **VM provisioning + IaC** chapters change, and this appendix replaces them.

---

## Mental map: AWS → Azure terminology

| AWS | Azure | Purpose |
|-----|-------|---------|
| EC2 Instance | Virtual Machine (VM) | the compute |
| AMI | VM Image | OS template |
| Security Group | Network Security Group (NSG) | firewall rules |
| VPC | Virtual Network (VNet) | private network |
| Subnet | Subnet | same concept |
| Elastic IP | Public IP Address (Standard, Static) | stable public IP |
| Key Pair | SSH Key | SSH auth |
| IAM User | Entra ID user / Service Principal | identity |
| S3 | Blob Storage | object storage |
| ECR | Azure Container Registry (ACR) | image registry |
| CloudFormation | ARM / Bicep | native IaC |
| — | Resource Group | Azure-only: logical container for grouped resources |

**The biggest Azure-specific concept is the Resource Group.** Everything you create lives inside one. Delete the RG → everything inside it is deleted. Great for learning/cleanup.

---

## Part A — Azure VM manual deployment (replaces Chapter 05)

### 1. Account + guardrails

1. Create Azure account: https://azure.microsoft.com/free — $200 free credit + 12 months of free-tier services.
2. Enable MFA on your account (Security → Authentication methods).
3. **Create a budget** — Cost Management → Budgets → `$5` monthly → email alert.
4. Install the Azure CLI:

```bash
# Ubuntu / WSL
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash

# macOS
brew install azure-cli

az --version
az login                     # opens a browser; sign in
```

5. Set the default subscription (if you have multiple):

```bash
az account list --output table
az account set --subscription "<subscription-name-or-id>"
```

---

### 2. Provision an Ubuntu VM (one CLI command)

Unlike AWS, you can do the whole launch from one Azure CLI command:

```bash
# Pick a region close to you (list them with: az account list-locations -o table)
LOCATION=eastus
RG=fortune-rg
VM=fortune-dev

# Create a resource group (logical bucket for all fortune resources)
az group create -n "$RG" -l "$LOCATION"

# Create the VM
az vm create \
  --resource-group "$RG" \
  --name "$VM" \
  --image Ubuntu2404 \
  --size Standard_B1s \
  --admin-username azureuser \
  --generate-ssh-keys \
  --public-ip-sku Standard

# Open port 80 (HTTP) — port 22 is already open from the az vm create defaults
az vm open-port --resource-group "$RG" --name "$VM" --port 80 --priority 1001
az vm open-port --resource-group "$RG" --name "$VM" --port 443 --priority 1002
```

`--generate-ssh-keys` either reuses `~/.ssh/id_rsa.pub` or creates one. The command prints the public IP at the end.

Grab it any time:

```bash
az vm show -d -g "$RG" -n "$VM" --query publicIps -o tsv
```

**Restrict SSH to just your IP** (the default is 0.0.0.0/0 — not great):

```bash
MY_IP=$(curl -s https://checkip.amazonaws.com)/32
NSG_NAME=$(az network nsg list -g "$RG" --query "[0].name" -o tsv)

az network nsg rule create \
  --resource-group "$RG" --nsg-name "$NSG_NAME" \
  --name AllowSSHFromMe --priority 1000 \
  --source-address-prefixes "$MY_IP" --destination-port-ranges 22 \
  --access Allow --protocol Tcp --direction Inbound

# Remove the permissive default rule
az network nsg rule delete -g "$RG" --nsg-name "$NSG_NAME" --name default-allow-ssh || true
```

---

### 3. SSH in

```bash
IP=$(az vm show -d -g fortune-rg -n fortune-dev --query publicIps -o tsv)
ssh azureuser@"$IP"
```

From here, **everything in Chapter 05 §4 onward applies unchanged** — install packages, create the DB, run the app with systemd, set up Nginx. Just replace user `ubuntu` with `azureuser` in commands and systemd units.

Summary of the replacements:

| AWS chapter said | Azure equivalent |
|------------------|-----------------|
| `ubuntu@<ec2-ip>` | `azureuser@<vm-ip>` |
| `User=ubuntu` in systemd | `User=azureuser` |
| `sudo chown ubuntu:ubuntu` | `sudo chown azureuser:azureuser` |

Everything else — Postgres install, Nginx config, systemd unit, smoke tests — **is identical**.

---

### 4. Destroy when done (save money!)

```bash
az group delete --name fortune-rg --yes --no-wait
```

One command, the whole environment is gone. The single best feature of Resource Groups.

---

## Part B — Terraform for Azure (replaces Chapter 07)

Terraform works the same way — only the provider and resource types change. Same workflow: `init → plan → apply → destroy`.

### Install the Azure CLI (done above) and log in

```bash
az login
```

Terraform reads your credentials from the CLI's cached session. No keys in files.

### `infra-azure/` layout

Create this folder **alongside** your AWS `infra/` folder so you can keep both — great for showing multi-cloud awareness in interviews.

```bash
mkdir -p infra-azure && cd infra-azure
```

### `variables.tf`

```hcl
variable "location" {
  type    = string
  default = "eastus"
}

variable "vm_size" {
  type    = string
  default = "Standard_B1s"   # ~$8/month; smallest reasonable VM
}

variable "admin_username" {
  type    = string
  default = "azureuser"
}

variable "my_ip_cidr" {
  description = "Your public IP in CIDR form, e.g. 1.2.3.4/32"
  type        = string
}

variable "ssh_public_key_path" {
  type    = string
  default = "~/.ssh/id_rsa.pub"
}
```

### `terraform.tfvars` (gitignored)

```hcl
my_ip_cidr          = "1.2.3.4/32"
ssh_public_key_path = "~/.ssh/id_rsa.pub"
```

### `main.tf`

```hcl
terraform {
  required_version = ">= 1.9"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.3"
    }
  }
}

provider "azurerm" {
  features {}
}

# ---- Resource group (the magic bucket) ----
resource "azurerm_resource_group" "fortune" {
  name     = "fortune-rg"
  location = var.location
  tags     = { Project = "fortune-cookie" }
}

# ---- Virtual network + subnet ----
resource "azurerm_virtual_network" "fortune" {
  name                = "fortune-vnet"
  resource_group_name = azurerm_resource_group.fortune.name
  location            = azurerm_resource_group.fortune.location
  address_space       = ["10.0.0.0/16"]
}

resource "azurerm_subnet" "fortune" {
  name                 = "fortune-subnet"
  resource_group_name  = azurerm_resource_group.fortune.name
  virtual_network_name = azurerm_virtual_network.fortune.name
  address_prefixes     = ["10.0.1.0/24"]
}

# ---- Network Security Group (firewall) ----
resource "azurerm_network_security_group" "fortune" {
  name                = "fortune-nsg"
  location            = azurerm_resource_group.fortune.location
  resource_group_name = azurerm_resource_group.fortune.name

  security_rule {
    name                       = "SSH"
    priority                   = 1000
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "22"
    source_address_prefix      = var.my_ip_cidr
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTP"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTPS"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "fortune" {
  subnet_id                 = azurerm_subnet.fortune.id
  network_security_group_id = azurerm_network_security_group.fortune.id
}

# ---- Static public IP (equivalent of an Elastic IP) ----
resource "azurerm_public_ip" "fortune" {
  name                = "fortune-pip"
  resource_group_name = azurerm_resource_group.fortune.name
  location            = azurerm_resource_group.fortune.location
  allocation_method   = "Static"
  sku                 = "Standard"
}

# ---- NIC (the VM's virtual network card) ----
resource "azurerm_network_interface" "fortune" {
  name                = "fortune-nic"
  location            = azurerm_resource_group.fortune.location
  resource_group_name = azurerm_resource_group.fortune.name

  ip_configuration {
    name                          = "primary"
    subnet_id                     = azurerm_subnet.fortune.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.fortune.id
  }
}

# ---- The VM ----
resource "azurerm_linux_virtual_machine" "fortune" {
  name                = "fortune-dev"
  resource_group_name = azurerm_resource_group.fortune.name
  location            = azurerm_resource_group.fortune.location
  size                = var.vm_size
  admin_username      = var.admin_username
  network_interface_ids = [azurerm_network_interface.fortune.id]

  admin_ssh_key {
    username   = var.admin_username
    public_key = file(var.ssh_public_key_path)
  }

  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
    disk_size_gb         = 30
  }

  # Ubuntu 24.04 LTS
  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  tags = { Project = "fortune-cookie" }
}
```

### `outputs.tf`

```hcl
output "public_ip" {
  value       = azurerm_public_ip.fortune.ip_address
  description = "Paste this into deploy/inventory.ini"
}

output "ssh_command" {
  value = "ssh ${var.admin_username}@${azurerm_public_ip.fortune.ip_address}"
}
```

### Run it

```bash
cd infra-azure
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply             # takes ~2-3 minutes
terraform output public_ip
```

Destroy when done:

```bash
terraform destroy
```

That's the **entire** Azure provisioning story. ~200 lines of HCL, done.

---

## Part C — Ansible inventory for Azure

Nothing changes in the playbook itself. Only `deploy/inventory.ini`:

```ini
[web]
fortune ansible_host=<AZURE_VM_PUBLIC_IP> ansible_user=azureuser ansible_ssh_private_key_file=~/.ssh/id_rsa
```

Then your `ansible-playbook deploy/site.yml` from Chapter 06 works **without any changes**. That's the payoff of using Ansible instead of a bash script — it doesn't care what cloud the VM lives on.

---

## Part D — GitHub Actions with Azure

For the deploy workflow (`.github/workflows/deploy.yml` from Chapter 06 §4), only the secrets change:

| AWS secret | Azure equivalent |
|------------|-----------------|
| `EC2_HOST` | `AZURE_VM_HOST` (the public IP) |
| `EC2_USER` | `AZURE_VM_USER` (= `azureuser`) |
| `EC2_SSH_KEY` | `AZURE_VM_SSH_KEY` (the private key content) |
| `DB_PASSWORD` | `DB_PASSWORD` (unchanged) |

If you want **Terraform itself** to run in CI against Azure, authenticate via an Entra ID Service Principal. Create one:

```bash
az ad sp create-for-rbac \
  --name fortune-ci \
  --role Contributor \
  --scopes /subscriptions/$(az account show --query id -o tsv)
```

Copy the four values it prints (`appId`, `password`, `tenant`, plus your subscription id) into GitHub as secrets `ARM_CLIENT_ID`, `ARM_CLIENT_SECRET`, `ARM_TENANT_ID`, `ARM_SUBSCRIPTION_ID`. The `azurerm` provider reads those env vars automatically.

---

## Part E — Azure Container Registry (replaces Docker Hub / GHCR for Ch 08)

If you want to stay fully within Azure:

```bash
# Create a registry (names are globally unique — add your handle)
az acr create -n fortuneacr<yourhandle> -g fortune-rg --sku Basic --admin-enabled true

# Let your VM pull from it (simplest option: enable admin user)
az acr credential show -n fortuneacr<yourhandle>

# From your laptop:
az acr login -n fortuneacr<yourhandle>
docker tag fortune-backend:dev fortuneacr<yourhandle>.azurecr.io/fortune-backend:$(git rev-parse --short HEAD)
docker push fortuneacr<yourhandle>.azurecr.io/fortune-backend:$(git rev-parse --short HEAD)
```

On the VM, `docker login fortuneacr<yourhandle>.azurecr.io` with the admin credentials. GHCR is simpler for a portfolio project — use ACR only if you're specifically targeting Microsoft/Azure roles.

---

## Part F — Azure-native observability (optional)

Chapter 09's Prometheus + Grafana setup **works fine on an Azure VM** — same docker-compose. If you want to show off Azure-native tooling instead, look at:

- **Azure Monitor + Application Insights** — one SDK call and you get full APM.
- **Log Analytics Workspace** — queryable logs via KQL (Kusto Query Language).
- **Managed Grafana** — fully-managed Grafana PaaS (costs money; skip for learning).

For the portfolio, stick with the OSS Prometheus stack. Mention Azure Monitor in interviews: *"I'd swap in Azure Monitor for a pure-Azure shop, but I wanted to demonstrate the OSS standard."*

---

## Cost comparison (2026 pricing, approximate)

| Resource | AWS | Azure |
|----------|-----|-------|
| Smallest VM 24/7 | t3.micro ≈ $8/mo | B1s ≈ $8/mo |
| Static public IP | ~$3.60/mo if attached | ~$3.60/mo |
| 30GB disk | ~$2.40/mo | ~$2.40/mo |
| **Total idle** | **~$14/mo** | **~$14/mo** |

Both have generous **free tiers** for 12 months if you use the right instance family. Always `destroy` when done — both providers charge per-hour for VMs + per-month for public IPs.

---

## Which should you learn?

- **AWS:** bigger job market (~60% of postings), more depth per service.
- **Azure:** #2 and growing fast, dominant in enterprise + Microsoft shops.
- **Ideal:** build the project on AWS first (per the main roadmap), then do Part B (Terraform Azure) as a Week 6 stretch. Result: a repo with `infra/` AND `infra-azure/` = "I've shipped on both clouds" on your resume. That's rare and credible for a junior.

---

## Definition of Done (Azure stretch)

- [ ] `terraform apply` in `infra-azure/` creates all Azure resources.
- [ ] Same Ansible playbook deploys the app to the Azure VM.
- [ ] Same GitHub Actions workflow deploys to Azure when secrets are flipped.
- [ ] `terraform destroy` removes everything; `az group list` shows no `fortune-rg`.
- [ ] You can describe the AWS → Azure terminology mapping from memory.

Back to: [`05-deployment-ec2.md`](05-deployment-ec2.md) · [`07-terraform-iac.md`](07-terraform-iac.md)
