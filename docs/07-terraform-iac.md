# 07 — Terraform (Infrastructure as Code)

> Goal: **replace "click around the AWS console" with code.**
> After this chapter, `terraform apply` will create the VPC, security group, EC2, and Elastic IP from scratch. `terraform destroy` removes it all.
>
> **Prefer Azure?** Use [`appendix-azure.md`](appendix-azure.md) **Part B** for the Azure-provider equivalent (Resource Group, VNet, NSG, VM, Public IP). You can keep **both** `infra/` and `infra-azure/` in the repo — multi-cloud literacy is a resume win.

---

## Ansible vs Terraform — clear up the confusion now

| Question | Ansible | Terraform |
|----------|---------|-----------|
| What does it manage? | Things **inside** a machine (packages, files, services) | **The machines themselves** + cloud resources |
| Style | Imperative-ish (tasks) | Declarative (desired state) |
| State | Stateless | Remembers what it created (state file) |
| When to use | Configure an existing server | Provision the server |

Rule of thumb: **Terraform makes the EC2. Ansible configures it.** You use both.

---

## Install Terraform

```bash
# Ubuntu/WSL
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install -y terraform

# macOS
brew tap hashicorp/tap
brew install hashicorp/tap/terraform

# verify
terraform -version   # v1.9+
```

Configure AWS credentials (reuse the IAM user from Chapter 05):

```bash
aws configure
# Access Key ID + Secret + region (us-east-1) + json
```

Install AWS CLI if you don't have it: `sudo apt install awscli` or `brew install awscli`.

---

## Layout

```
infra/
├── main.tf              AWS resources
├── variables.tf         inputs
├── outputs.tf           what to print after apply
├── terraform.tfvars     your actual values (gitignored)
└── .terraform.lock.hcl  auto-generated, DO commit this
```

```bash
mkdir -p infra && cd infra
```

---

## 1. `variables.tf`

```hcl
variable "region" {
  type    = string
  default = "us-east-1"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "key_name" {
  description = "Name of the EC2 key pair created in the AWS console (Chapter 05)"
  type        = string
}

variable "my_ip_cidr" {
  description = "Your public IP in CIDR form, e.g. 1.2.3.4/32"
  type        = string
}
```

## 2. `terraform.tfvars` (gitignored)

```hcl
key_name   = "fortune-key"
my_ip_cidr = "1.2.3.4/32"   # get yours from https://checkip.amazonaws.com
```

## 3. `main.tf`

```hcl
terraform {
  required_version = ">= 1.9"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
  }
}

provider "aws" {
  region = var.region
}

# --- Find the latest Ubuntu 24.04 AMI so we don't hardcode an ID ---
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]   # Canonical's AWS account
  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }
}

# --- Networking: use the default VPC, it's fine for this project ---
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# --- Security group ---
resource "aws_security_group" "fortune" {
  name        = "fortune-sg"
  description = "Fortune cookie app"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH from me"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "fortune-sg" }
}

# --- EC2 ---
resource "aws_instance" "fortune" {
  ami                         = data.aws_ami.ubuntu.id
  instance_type               = var.instance_type
  key_name                    = var.key_name
  vpc_security_group_ids      = [aws_security_group.fortune.id]
  subnet_id                   = tolist(data.aws_subnets.default.ids)[0]
  associate_public_ip_address = true

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  tags = {
    Name    = "fortune-dev"
    Project = "fortune-cookie"
  }
}

# --- Static public IP so rebuilds don't change the address ---
resource "aws_eip" "fortune" {
  instance = aws_instance.fortune.id
  domain   = "vpc"
  tags     = { Name = "fortune-eip" }
}
```

## 4. `outputs.tf`

```hcl
output "public_ip" {
  value       = aws_eip.fortune.public_ip
  description = "Paste this into deploy/inventory.ini"
}

output "ssh_command" {
  value = "ssh -i ~/.ssh/${var.key_name}.pem ubuntu@${aws_eip.fortune.public_ip}"
}
```

## 5. `.gitignore` additions

Add to the repo root `.gitignore` (already there from the scaffold):

```
infra/terraform.tfstate*
infra/.terraform/
infra/terraform.tfvars
```

---

## 6. Workflow

```bash
cd infra
terraform init                    # downloads AWS provider
terraform fmt                     # auto-format (do before every commit)
terraform validate                # syntax check
terraform plan                    # SHOW me what you'll do — ALWAYS READ THIS
terraform apply                   # actually do it
```

Apply will print your public IP. Copy it into `deploy/inventory.ini`, then run the Ansible playbook:

```bash
cd ../deploy
# edit inventory.ini with the new IP
ansible-playbook site.yml
```

Done. You just provisioned infra + configured the machine with two commands.

**Tear it down:**

```bash
cd ../infra
terraform destroy
```

The EC2, security group, and EIP are gone. AWS bill stops.

---

## 7. State file — the one rule you must not break

`terraform.tfstate` is the **source of truth** about what Terraform created. **Never delete it.**

For a solo project, leaving it on disk is fine. For teams, you'd use a **remote backend** (S3 + DynamoDB for locking). Mentioning this in interviews earns points:

> "For this project I used local state because I'm the only user. In a team I'd put state in an S3 backend with DynamoDB locking so two people can't `apply` at the same time."

---

## 8. Glue Terraform output → Ansible inventory (nice-to-have)

Instead of hand-copying the IP, add to `deploy/` a script `generate-inventory.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail
IP=$(terraform -chdir=../infra output -raw public_ip)
cat > inventory.ini <<EOF
[web]
fortune ansible_host=$IP ansible_user=ubuntu ansible_ssh_private_key_file=~/.ssh/fortune-key.pem
EOF
echo "inventory written for $IP"
```

Now your flow is:

```bash
terraform -chdir=infra apply -auto-approve
./deploy/generate-inventory.sh
ansible-playbook -i deploy/inventory.ini deploy/site.yml
```

Three commands, fresh cloud environment. That's the magic sentence on your resume.

---

## 9. Common Terraform gotchas

| Symptom | Cause / Fix |
|---------|-------------|
| `No valid credential sources found` | Run `aws configure`, check `~/.aws/credentials` |
| `InvalidKeyPair.NotFound` | `key_name` in tfvars doesn't match the name in the AWS console |
| Apply makes a new EC2 every time | You changed something that forces-replaces. Check the plan output for `-/+` markers |
| `terraform apply` destroys your EC2 when you don't expect it | You removed the resource block from `.tf` files. Never do this without thinking |
| State file corrupted | `terraform state list`, `terraform state rm <resource>`, then re-import. Rare for beginners |

---

## Definition of Done

- [ ] `terraform apply` creates the infra from empty.
- [ ] `terraform destroy` removes it cleanly.
- [ ] The Ansible playbook still works against the Terraform-created EC2.
- [ ] `terraform.tfstate` is NOT in git.
- [ ] `.terraform.lock.hcl` IS in git (pins provider versions).

Next: [`08-docker-containerization.md`](08-docker-containerization.md).
