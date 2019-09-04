import fauxfactory
import pytest

from cfme import test_requirements
from cfme.control.explorer.policies import VMControlPolicy
from cfme.infrastructure.provider.virtualcenter import VMwareProvider
from cfme.markers.env_markers.provider import ONE_PER_TYPE
from cfme.utils.appliance.implementations.ui import navigate_to
from cfme.utils.conf import credentials
from cfme.utils.update import update
from cfme.utils.wait import wait_for


pytestmark = [
    pytest.mark.ignore_stream("upstream"),
    pytest.mark.long_running,
    pytest.mark.provider([VMwareProvider], selector=ONE_PER_TYPE, scope="module"),
    test_requirements.ansible,
]


@pytest.fixture(scope="module")
def ansible_action(appliance, ansible_catalog_item):
    action_collection = appliance.collections.actions
    action = action_collection.create(
        fauxfactory.gen_alphanumeric(),
        action_type="Run Ansible Playbook",
        action_values={
            "run_ansible_playbook": {
                "playbook_catalog_item": ansible_catalog_item.name
            }
        }
    )
    yield action

    action.delete_if_exists()


@pytest.fixture(scope="module")
def policy_for_testing(appliance, full_template_vm_modscope, provider, ansible_action):
    vm = full_template_vm_modscope
    policy = appliance.collections.policies.create(
        VMControlPolicy,
        fauxfactory.gen_alpha(),
        scope="fill_field(VM and Instance : Name, INCLUDES, {})".format(vm.name)
    )
    policy.assign_actions_to_event("Tag Complete", [ansible_action.description])
    policy_profile = appliance.collections.policy_profiles.create(
        fauxfactory.gen_alpha(), policies=[policy])
    provider.assign_policy_profiles(policy_profile.description)
    yield

    if policy.exists:
        policy.unassign_events("Tag Complete")
        provider.unassign_policy_profiles(policy_profile.description)
        policy_profile.delete()
        policy.delete()


@pytest.fixture(scope="module")
def ansible_credential(wait_for_ansible, appliance, full_template_modscope):
    credential = appliance.collections.ansible_credentials.create(
        fauxfactory.gen_alpha(),
        "Machine",
        username=credentials[full_template_modscope.creds]["username"],
        password=credentials[full_template_modscope.creds]["password"]
    )
    yield credential

    credential.delete_if_exists()


@pytest.mark.tier(3)
def test_action_run_ansible_playbook_localhost(
    appliance,
    request,
    ansible_catalog_item,
    ansible_action,
    policy_for_testing,
    full_template_vm_modscope,
    ansible_credential,
    ansible_service_request_funcscope,
    ansible_service_funcscope,
):
    """Tests a policy with ansible playbook action against localhost.

    Polarion:
        assignee: sbulage
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    with update(ansible_action):
        ansible_action.run_ansible_playbook = {"inventory": {"localhost": True}}
    added_tag = full_template_vm_modscope.add_tag()
    request.addfinalizer(lambda: full_template_vm_modscope.remove_tag(added_tag))
    wait_for(ansible_service_request_funcscope.exists, num_sec=600)
    ansible_service_request_funcscope.wait_for_request()
    view = navigate_to(ansible_service_funcscope, "Details")
    assert view.provisioning.details.get_text_of("Hosts") == "localhost"
    assert (
        view.provisioning.results.get_text_of("Status") == "successful"
        if appliance.version < "5.11"
        else "Finished"
    )


@pytest.mark.tier(3)
def test_action_run_ansible_playbook_manual_address(
    appliance,
    request,
    ansible_catalog_item,
    ansible_action,
    policy_for_testing,
    full_template_vm_modscope,
    ansible_credential,
    ansible_service_request_funcscope,
    ansible_service_funcscope,
):
    """Tests a policy with ansible playbook action against manual address.

    Polarion:
        assignee: sbulage
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    vm = full_template_vm_modscope
    with update(ansible_catalog_item):
        ansible_catalog_item.provisioning = {"machine_credential": ansible_credential.name}
    with update(ansible_action):
        ansible_action.run_ansible_playbook = {
            "inventory": {
                "specific_hosts": True,
                "hosts": vm.ip_address
            }
        }
    added_tag = vm.add_tag()
    request.addfinalizer(lambda: vm.remove_tag(added_tag))
    wait_for(ansible_service_request_funcscope.exists, num_sec=600)
    ansible_service_request_funcscope.wait_for_request()
    view = navigate_to(ansible_service_funcscope, "Details")
    assert view.provisioning.details.get_text_of("Hosts") == vm.ip_address
    assert (
        view.provisioning.results.get_text_of("Status") == "successful"
        if appliance.version < "5.11"
        else "Finished"
    )


@pytest.mark.tier(3)
def test_action_run_ansible_playbook_target_machine(
    appliance,
    request,
    ansible_catalog_item,
    ansible_action,
    policy_for_testing,
    full_template_vm_modscope,
    ansible_credential,
    ansible_service_request_funcscope,
    ansible_service_funcscope,
):
    """Tests a policy with ansible playbook action against target machine.

    Polarion:
        assignee: sbulage
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    vm = full_template_vm_modscope
    with update(ansible_action):
        ansible_action.run_ansible_playbook = {"inventory": {"target_machine": True}}
    added_tag = vm.add_tag()
    request.addfinalizer(lambda: vm.remove_tag(added_tag))
    wait_for(ansible_service_request_funcscope.exists, num_sec=600)
    ansible_service_request_funcscope.wait_for_request()
    view = navigate_to(ansible_service_funcscope, "Details")
    assert view.provisioning.details.get_text_of("Hosts") == vm.ip_address
    assert (
        view.provisioning.results.get_text_of("Status") == "successful"
        if appliance.version < "5.11"
        else "Finished"
    )


@pytest.mark.tier(3)
def test_action_run_ansible_playbook_unavailable_address(request, ansible_catalog_item,
        full_template_vm_modscope, ansible_action, policy_for_testing, ansible_credential,
        ansible_service_request_funcscope, ansible_service):
    """Tests a policy with ansible playbook action against unavailable address.

    Polarion:
        assignee: sbulage
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    vm = full_template_vm_modscope
    with update(ansible_catalog_item):
        ansible_catalog_item.provisioning = {"machine_credential": ansible_credential.name}
    with update(ansible_action):
        ansible_action.run_ansible_playbook = {
            "inventory": {
                "specific_hosts": True,
                "hosts": "unavailable_address"
            }
        }
    added_tag = vm.add_tag()
    request.addfinalizer(lambda: vm.remove_tag(added_tag))
    wait_for(ansible_service_request_funcscope.exists, num_sec=600)
    ansible_service_request_funcscope.wait_for_request()
    view = navigate_to(ansible_service, "Details")
    assert view.provisioning.details.get_text_of("Hosts") == "unavailable_address"
    assert view.provisioning.results.get_text_of("Status") == "failed"


@pytest.mark.tier(3)
def test_control_action_run_ansible_playbook_in_requests(request,
        full_template_vm_modscope, policy_for_testing, ansible_service_request_funcscope):
    """Checks if execution of the Action result in a Task/Request being created.

    Polarion:
        assignee: sbulage
        initialEstimate: 1/6h
        casecomponent: Ansible
    """
    vm = full_template_vm_modscope
    added_tag = vm.add_tag()
    request.addfinalizer(lambda: vm.remove_tag(added_tag))
    assert ansible_service_request_funcscope.exists
