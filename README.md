# RHEL-CIS

Ansible playbooks for applying CIS-oriented hardening to legacy RHEL systems.
These playbooks change system configuration; a successful run does not establish
CIS compliance. Review the selected tasks and validate them on a disposable test
host before applying them to an existing server.

## Repository layout and target systems

| Directory | Purpose |
| --- | --- |
| [rhel6-cis](rhel6-cis/) | RHEL 6 hardening, with a local `cis` role and section 1–9 task files. |
| [rhel7-cis](rhel7-cis/) | RHEL/CentOS 7 hardening, with a local `cis` role and section 1–6 task files. |
| [apache_install](apache_install/) | Separate Apache installation playbook and role. |
| [ansible](ansible/) | Miscellaneous repository material. |

The RHEL 7 role documentation identifies CIS Red Hat Enterprise Linux 7 Benchmark
v2.1.1 (2017) as its baseline. These are legacy targets; compatibility with newer
RHEL releases or current CIS benchmarks is not established.

## Prerequisites

- An Ansible control machine with SSH access to the selected target hosts.
- A remote account with root or sudo access, plus Python and package repositories
  appropriate for the target system.
- An Ansible version compatible with these legacy playbooks. The RHEL 7 role
  checks for Ansible 2.1 or later, while its bundled README says greater than 2.2.
  No tested version is pinned in this repository. Legacy `include` tasks and
  `version_compare` filters mean the latest Ansible is not necessarily compatible.

Review the role defaults and task files before running. Changes can affect SSH,
authentication, services, firewall rules, and boot settings.

## Inventory and execution

Choose the directory matching the target operating system. From the repository
root, for example:

```sh
cd rhel7-cis
```

For RHEL 6, use `cd rhel6-cis` instead. Both directories contain a `playbook.yml`
that runs their local `cis` role against all hosts in the supplied inventory.
Running from the selected directory also loads its local `ansible.cfg`.

Create your own inventory outside the checkout, for example
`~/cis-inventory.ini`, replacing the example hostname and SSH user:

```ini
[targets]
test-server.example.com ansible_user=admin
```

Always supply that inventory explicitly. The checked-in RHEL 7 `hosts` file
contains an existing hostname and should not be used unchanged. The RHEL 6
configuration disables SSH host-key checking; enable it for your environment,
for example with `export ANSIBLE_HOST_KEY_CHECKING=True`.

Inspect the selected hosts and tasks, then preview changes:

```sh
ansible-playbook -i ~/cis-inventory.ini playbook.yml --syntax-check
ansible-playbook -i ~/cis-inventory.ini playbook.yml --list-hosts
ansible-playbook -i ~/cis-inventory.ini playbook.yml --list-tasks
ansible-playbook -i ~/cis-inventory.ini playbook.yml --become --check --diff
```

Check mode is a preview, not proof that all controls work: command-based tasks
may be skipped or behave differently. After reviewing the preview on a test
host, apply the playbook:

```sh
ansible-playbook -i ~/cis-inventory.ini playbook.yml --become
```

Add `--ask-become-pass` if sudo requires a password.

## Configuration

Use inventory variables or a separate YAML variables file instead of editing
role defaults. Pass a variables file with `-e @/path/to/overrides.yml`.

- [RHEL 6 defaults](rhel6-cis/roles/cis/defaults/main.yml) include
  `configure_aide`, `lock_inactive`, `enable_iptables`, and `disable_ipv6`.
  Section tags such as `section1` are defined in the
  [task entry point](rhel6-cis/roles/cis/tasks/main.yml).
- [RHEL 7 defaults](rhel7-cis/roles/cis/defaults/main.yml) include
  `rhel7cis_section1` through `rhel7cis_section6` (all enabled by default),
  service settings, and `rhel7cis_notauto` (disabled by default).
  Use these defaults as the source of truth; some examples in the bundled
  [role README](rhel7-cis/roles/cis/README.md) differ from this checkout.

## Control coverage and validation

Inspect the active [RHEL 6 tasks](rhel6-cis/roles/cis/tasks/) and
[RHEL 7 tasks](rhel7-cis/roles/cis/tasks/) for the controls you need. Coverage is
partial: some controls are commented out, and numerous RHEL 7 tasks tagged
`notimplemented` run only `/bin/true`. For example, audit rules 4.1.4–4.1.7
in [section4.yml](rhel7-cis/roles/cis/tasks/section4.yml) are placeholders, not
implemented audit configuration. An `ok` result for these tasks does not mean
the control was checked or remediated.

The [RHEL 7 test playbook](rhel7-cis/tests/test.yml) references
`role_under_test`, which is not a role provided by this checkout. It needs role
discovery setup before use. Use the main playbook for the inspection commands
above, and independently audit the resulting host configuration against the
benchmark required by your organization.

### OS guard regression checks

Both roles check the RedHat OS family and their required major version before
loading configuration tasks. Missing facts also cause the guard to fail. The
guards use the `always` tag; explicitly skipping that tag bypasses them.

Run the focused regression checks in a Python environment with `ansible-core`
and PyYAML installed and `ansible-playbook` on `PATH`:

```sh
python -m unittest discover -s tests -v
```

These checks execute each role's actual first task against synthetic OS facts,
followed by a harmless sentinel representing a configuration change. They check
supported hosts, unsupported hosts, missing facts, section-tag selection, and
check mode. They also verify that the guard is first and that no role dependencies
precede it. Tested with ansible-core 2.16.14; this isolated guard test does not
establish compatibility of the full legacy roles with that version of Ansible.
