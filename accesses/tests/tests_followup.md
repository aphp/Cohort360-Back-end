## Tests to be made for app users

### Glossary

*Data access rights:*
- right_read_patient_nominative
- right_search_patient_with_ipp
- right_read_patient_pseudo_anonymised

*Admin rights:*
- right_manage_data_accesses_same_level
- right_read_data_accesses_same_level
- right_manage_data_accesses_inferior_levels
- right_read_data_accesses_inferior_levels

*Admin managing rights:*
- right_manage_admin_accesses_same_level
- right_read_admin_accesses_same_level
- right_manage_admin_accesses_inferior_levels
- right_read_admin_accesses_inferior_levels

*Main admin rights:*
- right_manage_roles

*Require admin managing or main admin rights*:
- right_read_users

*Close an access:* set end_datetime to now()


### Unit tests

- [ ] Q_role_where_right_is_true
- [ ] Q_readable_with_admin_mng
- [ ] Q_readable_with_data_admin
- [ ] Q_role_on_lower_levels
- [ ] Q_readable_with_role_admin_access
- [ ] Q_readable_with_review_jup_mng_access
- [ ] Q_readable_with_jupyter_mng_access
- [ ] Q_readable_with_review_csv_mng_access
- [ ] Q_readable_with_csv_mng_access
- [ ] get_specific_roles
- [ ] get_all_readable_accesses_perimeters
- [ ] get_all_level_parents_perimeters
- [ ] can_roles_manage_access
- [ ] get_assignable_roles_on_perimeter
- [ ] get_all_user_managing_accesses_on_perimeter
- [ ] get_user_valid_manual_accesses_queryset
- [ ] get_user_dict_data_accesses

- [ ] build_data_rights
- [ ] get_data_rights_on_roots
- [ ] rootify_perimeters

### Functional tests on /accesses/

#### SUPER ADMIN
- As a user with all the rights on the top perimeter, ...
  - [x] I cannot delete an access whom the start_datetime has passed
  - [x] I cannot update any datetime of an access
  - [x] I cannot update any other field than datetimes of an access
  - [x] I cannot close an access whom end_datetime has passed
  - [x] I cannot close an access whom start_datetime has not passed

#### MAIN ADMIN


#### GET

`/accesses/` :
- [x] As a user with all the rights, I can get accesses given query parameters
    - [x] Searching on (firstname, lastname, email, user's provider_username) using 'search'
    - [ ] Searching on (perimeter_id) using 'search'  (code not ready)
    - [ ] Filtering on target_perimeter_id (code not ready)
    - [ ] Searching on perimeter_name (code not ready)
    - [x] Filtering with profile_id
    - [x] Filtering with profile_lastname
    - [x] Filtering with profile_firstname
    - [x] Filtering with profile_email
    - [x] Filtering with profile_user_id

- For each group of rights as set in rules.md, :
  - If the group has same/inferior levels different rights :
    - [x] as a user with access reading right on same level on a perimeter, I can see the accesses with readable roles on that perimeter
    - [x] as a user with access reading right on inferior levels on a perimeter, I can see the accesses with readable roles on this perimeter's children
    - [x] (403) as a user with access reading right on inferior levels on a perimeter that has no children, I have no permission to read perimeters
  - If the group does not have same/inferior levels different rights, but have underlying rights to manage :
    - [x] as a user with any of the group rights, I can see the accesses with readable roles on all perimeters
- [x] For each two groups of rights, as a user with two rights from each, given the rules set previously, I can see the union of the accesses I could see with each 

`/accesses/my-accesses` :
- [ ] As a user, I can get the valid accesses I possess

`/accesses/my-rights` :
- [ ] As a user, I can get my top rights (describe 3 cases)
- [ ] As a user, I can get my rights on specific perimeters (describe 3 cases)


#### POST

For any of the groups of rights A that has the upper hand on on groups Bs (cf. rules.md):
- [x] As a user with the right to manage B-role-accesses on the same level, :
  - [x] I can create an access with allowed roles to a user on the same perimeter
  - [x] I cannot create an access with any unallowed role to a user on the same perimeter
  - [x] I cannot create an access with allowed roles to a user on any child perimeter
  - [x] I cannot create an access with allowed roles to a user on any parent perimeter
- [x] As a user with the right to manage B-role-accesses on the inferior levels, :
  - [x] I can create an access with allowed roles to a user on any child perimeter
  - [x] I cannot create an access with any unallowed role to a user on any child perimeter
  - [x] I cannot create an access with allowed roles to a user on the same perimeter
  - [x] I cannot create an access with allowed roles to a user on any parent perimeter
- [x] If group A does not have same/inferior levels right distinction : As a user with any right from group A, :
  - [x] I can create an access with allowed roles to a user on any perimeter
  - [x] I cannot create an access with any unallowed role to a user on any perimeter

#### DELETE

- [x] As an admin on main care_site, I cannot delete a user access for user to hospital2
- [x] As a local admin on hospital2, I can delete a user access for user2 to hospital2
- [x] As a local admin on hospital2, I can delete a user access for user1 to hospital3
- [x] As a local admin on hospital1, I can't delete a user access for user2 to hospital2
- [x] As a local admin on hospital2, I cannot delete a user access if the access already started
- [x] As a user with all the rights on the top care_site I cannot delete an access to a user on any care_site with a role that has any rights, and whom the start_datetime has passed

For any of the groups of rights A that has the upper hand on on groups Bs (cf. rules.md):
- [x] As a user with the right to manage and read B-role-accesses on the same level, :
  - [x] I can delete an access with **allowed** roles to a user on the same perimeter
  - [x] I cannot delete an access with any **unallowed** role to a user on the same perimeter
  - [x] (return _unfound_) I cannot delete an access with a **unreadable** role to a user on the same perimeter
  - [x] (return _unfound_) I cannot delete an access with **allowed** roles to a user on a child perimeter
  - [x] (return _unfound_) I cannot delete an access with **allowed** roles to a user on a parent perimeter
- [x] As a user with the right to manage on the same level and read on inferior levels B-role-accesses, :
  - [x] I cannot delete an access with **allowed** roles to a user on a child perimeter
  - [x] (return _unfound_) I cannot delete an access with **allowed** roles to a user on a the same perimeter
  - [x] (return _unfound_) I cannot delete an access with **allowed** roles to a user on a parent perimeter

- [x] As a user with the right to manage and read B-role-accesses on the inferior levels, :
  - [x] I can delete an access with an **allowed** role to a user on a child perimeter
  - [x] I cannot delete an access with an **unallowed** role to a user on a child perimeter
  - [x] (return _unfound_) I cannot delete an access with an **unreadable** role to a user on a child perimeter
  - [x] (return _unfound_) I cannot delete an access with an **allowed** role to a user the same perimeter
  - [x] (return _unfound_) I cannot delete an access with an **allowed** role to a user a parent perimeter
- [x] As a user with the right to manage on inferior levels and read on the same level B-role-accesses, :
  - [x] I cannot delete an access with **allowed** roles to a user on the same perimeter
  - [x] (return _unfound_) I cannot delete an access with **allowed** roles to a user on a parent perimeter
  - [x] (return _unfound_) I cannot delete an access with **allowed** roles to a user on the same perimeter
- 
- [x] If group A does not have same/inferior levels right distinction: As a user with a right from group A, :
  - [x] I can delete an access with **allowed** roles to a user on a perimeter
  - [x] I cannot delete an access with a **unallowed** role to a user on a perimeter
  - [x] (return _unfound_) I cannot delete an access with a **unreadable** role to a user on a perimeter

#### PATCH

`/accesses/{id}` :

- [x] As a main admin, I cannot update a user access for user1 to hospital3
- [x] As a local admin on hospital2, I can update a user access for user1 to hospital3 but role_id, care_site_id, and provider_history_id won't change
- [x] As a local admin on hospital1, I can't update a user access for user2 to hospital2
- [x] As an admin on care_site H2, I cannot update a user access for user1 to hospital3 with a None value
- [x] As an admin on care_site H2, I can update a user access for user1 to hospital3 with a None start_datetime, it will be set as now
- [x] As an admin on care_site H2, I can update a user access for user1 to hospital3 with start_datetime empty and an end_date
- [x] As an admin on care_site H2, I cannot update a start/end_datetime with a date that is already passed
- [x] As an admin on care_site H2, I cannot update a start/end_datetime when the current one set is passed
- [x] As a local admin on hospital2, I can close a user access for user1 to hospital3
- [x] As a local admin on hospital2, I cannot close a user access that has already ended
- [x] As a local admin on hospital2, I cannot close a user access that has already ended

For any of the groups of rights A that has the upper hand on on groups Bs (cf. rules.md):
- [x] As a user with the right to manage and read B-role-accesses on the same level, :
  - [x] I can update an access with **allowed** roles to a user on the same perimeter
  - [x] I cannot update an access with any **unallowed** role to a user on the same perimeter
  - [x] (return _unfound_) I cannot update an access with a **unreadable** role to a user on the same perimeter
  - [x] (return _unfound_) I cannot update an access with **allowed** roles to a user on a child perimeter
  - [x] (return _unfound_) I cannot update an access with **allowed** roles to a user on a parent perimeter
- [x] As a user with the right to manage on the same level and read on inferior levels B-role-accesses, :
  - [x] I cannot update an access with **allowed** roles to a user on a child perimeter
  - [x] (return _unfound_) I cannot update an access with **allowed** roles to a user on a the same perimeter
  - [x] (return _unfound_) I cannot update an access with **allowed** roles to a user on a parent perimeter

- [x] As a user with the right to manage and read B-role-accesses on the inferior levels, :
  - [x] I can update an access with an **allowed** role to a user on a child perimeter
  - [x] I cannot update an access with an **unallowed** role to a user on a child perimeter
  - [x] (return _unfound_) I cannot update an access with an **unreadable** role to a user on a child perimeter
  - [x] (return _unfound_) I cannot update an access with an **allowed** role to a user the same perimeter
  - [x] (return _unfound_) I cannot update an access with an **allowed** role to a user a parent perimeter
- [x] As a user with the right to manage on inferior levels and read on the same level B-role-accesses, :
  - [x] I cannot update an access with **allowed** roles to a user on the same perimeter
  - [x] (return _unfound_) I cannot update an access with **allowed** roles to a user on a parent perimeter
  - [x] (return _unfound_) I cannot update an access with **allowed** roles to a user on the same perimeter

- [x] If group A does not have same/inferior levels right distinction: As a user with a right from group A, :
  - [x] I can update an access with **allowed** roles to a user on a perimeter
  - [x] I cannot update an access with a **unallowed** role to a user on a perimeter
  - [x] (return _unfound_) I cannot update an access with a **unreadable** role to a user on a perimeter



`/accesses/{id}/close` :
'close' call will set end_datetime to now().

For any of the groups of rights A that has the upper hand on on groups Bs (cf. rules.md):
- [x] As a user with the right to manage and read B-role-accesses on the same level, :
  - [x] I can close an access with **allowed** roles to a user on the same perimeter
  - [x] I cannot close an access with any **unallowed** role to a user on the same perimeter
  - [x] (return _unfound_) I cannot close an access with a **unreadable** role to a user on the same perimeter
  - [x] (return _unfound_) I cannot close an access with **allowed** roles to a user on a child perimeter
  - [x] (return _unfound_) I cannot close an access with **allowed** roles to a user on a parent perimeter
- [x] As a user with the right to manage on the same level and read on inferior levels B-role-accesses, :
  - [x] I cannot close an access with **allowed** roles to a user on a child perimeter
  - [x] (return _unfound_) I cannot close an access with **allowed** roles to a user on a the same perimeter
  - [x] (return _unfound_) I cannot close an access with **allowed** roles to a user on a parent perimeter

- [x] As a user with the right to manage and read B-role-accesses on the inferior levels, :
  - [x] I can close an access with an **allowed** role to a user on a child perimeter
  - [x] I cannot close an access with an **unallowed** role to a user on a child perimeter
  - [x] (return _unfound_) I cannot close an access with an **unreadable** role to a user on a child perimeter
  - [x] (return _unfound_) I cannot close an access with an **allowed** role to a user the same perimeter
  - [x] (return _unfound_) I cannot close an access with an **allowed** role to a user a parent perimeter
- [x] As a user with the right to manage on inferior levels and read on the same level B-role-accesses, :
  - [x] I cannot close an access with **allowed** roles to a user on the same perimeter
  - [x] (return _unfound_) I cannot close an access with **allowed** roles to a user on a parent perimeter
  - [x] (return _unfound_) I cannot close an access with **allowed** roles to a user on the same perimeter

- [x] If group A does not have same/inferior levels right distinction: As a user with a right from group A, :
  - [x] I can close an access with **allowed** roles to a user on a perimeter
  - [x] I cannot close an access with a **unallowed** role to a user on a perimeter
  - [x] (return _unfound_) I cannot close an access with a **unreadable** role to a user on a perimeter

### Functional tests on /profiles/

#### GET

- [x] As a user with read_users right, I can get all profiles
- [x] As a user with read_users right, I can get profiles given query parameters :
  - [x] provider_id
  - [x] source
  - [x] cdm_source
  - [x] user
  - [x] provider_source_value
  - [x] provider_name
  - [x] lastname
  - [x] firstname
  - [x] email
  - [x] provider_history_id
  - [x] id
  - [x] is_active
- [x] As a user with all the rights but not read_users one, I cannot see any profile


#### POST

`/profiles/` :
- [x] As a user with right_add_users, :
  - [x] I can create a new profile for a user that has no manual profile yet
  - [x] when creating a new manual profile the fields valid_start_datetime, valid_end_datetime and is_active will actually fill manual_valid_start_datetime, etc.
  - [x] I can create a profile for a non existing user, this will also create a User
- [x] As a user with everything but right_add_users, I cannot create a new profile
- [x] As a user with all the rights, :
  - [x] I cannot create a new profile to a user that already has a manual profile
  - [x] when creating a new manual profile specifying a source will return 400.
  - [x] when creating a new manual profile specifying a value to one of the previous fields AND to its manual_version will return 400.
  - [x] I cannot create a profile for a non existing user if id is not validated with check_id_aph
  - [x] I cannot create a profile for a non existing user if provider_id is not found by get_provider_id

`/profiles/check` :
- As a user with right_add_users, can check the existence of a user on the control API:
  - [x] and it returns User and Manual profile if it exists
  - [x] and it returns None if the API's response is empty
  - [x] and it returns with empty user and profile if user is not in database
  - [x] and it returns with empty profile if user has no manual profile
- [x] As a user with everything but right_add_users, I cannot check the existence of a user on the control API
- [x] (400) As a user with all the rights, I cannot call it without providing 'user_id' parameter


#### PATCH

- [x] As a user with right_edit_users, I can edit a profile
- [x] As a user with everything but right_edit_users, I cannot edit a profile
- [x] As a user with all the rights, I cannot edit a profile with certain fields

#### DELETE

- [x] As a user with all the rights, I cannot delete a profile


### Functional tests on /roles/

#### GET

`/roles/` :
- [x] As a user with no right, I can get all roles
- [x] As a user with no right, I can get roles filtered given query parameters:
  - [x] name
  - [x] any right

`/roles/assignable` :
- [x] As a user with a right to manage accesses, I can get the roles I can assign to another user on a perimeter P given rules.md
- [x] As a user with a right to manage accesses, I cannot call _assignable_ without perimeter_id parameter

#### POST

- [x] As a user with right_manage_roles, I can create a role
- [x] As a user with everything but right_manage_roles, I cannot create a role

#### PATCH

- [x] As a user with right_manage_roles, I can edit a role
- [x] As a user with everything but right_manage_roles, I cannot edit a role

#### DELETE

- [x] As a user with all the rights, I cannot delete a role


### Functional tests on /perimeters/

#### GET

`/perimeters/` :
- As a simple user, I can get all perimeters: 
  - [x] in a list view
  - [x] in a tree view
- As a user with no right, I can get perimeters filtered given query parameters:
  - [x] name
  - [x] type_source_value
  - [x] source_value

`/perimeters/{id}/children` :
- [x] As a simple user, I can get the children of a perimeter

`/perimeters/manageable` :
For any of the groups of rights that has the upper hand on another group (cf. rules.md):
- (tree view) As a user :
  - [x] with the right to manage accesses on the same level of a perimeter P, _manageable_ will return the perimeter P
  - [x] with the right to manage accesses on the inferior levels of a perimeter P, _manageable_ will return the perimeter P's children
  - [x] with the right to manage accesses on both same and inferior levels of a perimeter P, _manageable_ will return the perimeter P with its children
  - [x] with the right to manage accesses on both same and inferior levels of a perimeter P and one of its siblings, _manageable_ will return the two perimeters with their children
  - [x] with the right to read accesses on both same and inferior levels of a perimeter P, _manageable_ will return an empty list
  - [x] with the right to manage accesses on the inferior levels of the top level, _manageable_ will return all perimeters except the top one
  - [x] with the right to manage accesses on both same and inferior levels of the top level, _manageable_ will return all perimeters
  - [x] with the right to manage accesses on both same and inferior levels of the top level, _manageable_ will return all perimeters except most inferior perimeter if nb_levels=2

#### MANAGE

- As a user with all the rights, :
  - [x] I cannot create a perimeter
  - [x] I cannot edit a perimeter
  - [x] I cannot delete a perimeter
