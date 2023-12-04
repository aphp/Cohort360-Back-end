## Tests to be made for app users

### Unit tests

- [x] get_all_cs_to_cs_relationships
- [x] get_direct_children_cs_ids
- [x] get_direct_parent_care_site_ids
- [x] get_all_parent_care_sites_ids
    - [x] care site 32
    - [x] care site 21, 23

- [ ] get_next_maintenance

### Functional tests on /care-sites/

#### GET

`/care-sites/` :
- [x] As a simple user, I can get all care_sites. With weak filter on _care_site_name_, _care_site_short_name_ and _care_site_type_source_value_, and a search on .
- [ ] As a simple user, I can get care_sites with a weak filter on _care_site_name_, _care_site_short_name_ and _care_site_type_source_value_.
- [ ] As a simple user, I can get care_sites with a general search parameter on _care_site_name_ and _care_site_short_name_.

`/care-sites/manageable` :
- [ ] As any user, I can get the care-sites I can give an access on, returned within a tree format.
  - [ ] Case with edit_roles right: should return all the care-sites
  - [ ] Case with right_manage_admin_accesses_same_level on a care-site, should return this care-site
  - [ ] Case with right_manage_admin_accesses_inferior_levels on a care-site, should return the children care-sites with the restriction on types from AUTHORIZED_CARE_SITE_TYPE_SOURCE_VALUE.
  - [ ] Case with right_manage_data_accesses_same_level on a care-site, should return this care-site
  - [ ] Case with right_manage_data_accesses_inferior_levels on a care-site, should return the children care-sites with the restriction on types from AUTHORIZED_CARE_SITE_TYPE_SOURCE_VALUE.

`/care-sites/{id}/children` :
- [x] As a simple user, I can get the children care_sites of a specific care_sites

#### OTHERS

- [ ] As any user, a PUT request returns 403.
- [ ] As any user, a POST request returns 403.
- [ ] As any user, a PATCH request returns 403.
- [ ] As any user, a DELETE request returns 403.

### Functional tests on /users/

`/care-sites/` :
- [x] As a user with read_users right, I can get all providers with full data
- [ ] As a user without read_users right, I can get providers without full data.

### Functional tests on /maintenances/

#### GET

`/maintenances/` :
- [x] As a user with no right, I can get all maintenance phases
- [x] As a user with no right, I can get maintenance phases filtered given query parameters:
  - [x] subject
  - [x] search (on 'subject')
  - [x] start_datetime
  - [x] end_datetime

`/maintenances/next` :
- [x] As a user with no right, I can get the next maintenance phase, given the rules:
  - [x] if no phase with start_datetime > now or end_datetime > now, return {}
  - [x] if there are one or more phases with start_datetime < now < end_datetime return the one with highest end_datetime
  - [x] if there are no phase with start_datetime < now < end_datetime, and if there are one or more phases with now < start_datetime, return the one with lowest end_datetime

#### POST

- [x] As a user with right_full_admin, I can create a maintenance phase
- [x] As a user with everything but right_full_admin, I cannot create a maintenance phase
- [x] As a user with all the rights, I cannot create a maintenance phase if start_datetime > end_datetime

#### PATCH

- [x] As a user with right_full_admin, I can edit a maintenance phase
- [x] As a user with everything but right_full_admin, I cannot edit a maintenance phase
- [x] As a user with all the rights, I cannot edit a maintenance phase with start_datetime > end_datetime

#### DELETE

- [x] As a user with right_full_admin, I can delete a maintenance phase
- [x] As a user with everything but right_full_admin, I cannot delete a maintenance phase


#### OTHERS

- [ ] As any user, a PUT request returns 403.
- [x] As any user, a POST request returns 403.
- [x] As any user, a PATCH request returns 403.
- [x] As any user, a DELETE request returns 403.

### Functional tests on /maintenances/

`/maintenances/` :
- [ ] As a user authentified with no rights, I can read maintenances phases
- [ ] As a user authentified with no rights, I cannot patch a maintenance phase
- [ ] As a user authentified with no rights, I cannot create a maintenance phase
- [ ] As a user authentified with no rights, I cannot delete a maintenance phase

- [ ] As a user authentified with right_full_admin, I cann patch a maintenance phase
- [ ] As a user authentified with right_full_admin, I cann create a maintenance phase
- [ ] As a user authentified with right_full_admin, I cann delete a maintenance phase

`/maintenances/next` :
- [ ] As a user authentified with no rights, I can read next maintenance


#### OTHERS

- [ ] As any user, a PUT request returns 403.
- [x] As any user, a POST request returns 403.
- [x] As any user, a PATCH request returns 403.
- [x] As any user, a DELETE request returns 403.

