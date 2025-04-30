
# External _Authentication/Identity Services_

---

  **Cohort360-backend** allows to define hooks for **authentication** and **identity checking** in the _admin_cohort_ [App Config](../admin_cohort/apps.py).  

## 🔸Authentication
  Under the `HOOKS` dictionary setting, add a key `USER_AUTHENTICATION` that takes a list of Python valid paths to callables, ex:  
```python
HOOKS = {"USER_AUTHENTICATION": ["admin_cohort.tools.hooks.authenticate_user_via_service_1",
                                 "admin_cohort.tools.hooks.authenticate_user_via_service_2",
                                 "admin_cohort.tools.hooks.authenticate_user_via_service_3"
                                 ]
         }
```

  > Each hook must accept a couple of credentials as arguments ```username: str, password: str``` and return a boolean indicating authentication 
    status.
  
  * If _authentication_ hooks are defined, they are given precedence to authenticate users before falling back to local credentials validation.  
    They would run one after another, in their order of definition, until a `True` value is returned (i.e. a hook has successfully authenticated the 
    user credentials).  

## 🔸Check User Identity
  Under the `HOOKS` dictionary setting, add a key `USER_IDENTITY` that takes a list of Python valid paths to callables, ex:  
```python
HOOKS = {"USER_IDENTITY": ["admin_cohort.tools.hooks.check_user_identity_via_service_1",
                           "admin_cohort.tools.hooks.check_user_identity_via_service_2",
                           "admin_cohort.tools.hooks.check_user_identity_via_service_3"
                           ]
         }
```

  > Each hook must accept a single argument ```username: str``` and return a _**dict**_ with basic user identity data as keys if user was found or 
    _**None**_ otherwise.
```python
user_identity = {"username": "<username>",
                 "firstname": "<firstname>",
                 "lastname": "<lastname>",
                 "email": "<email>"
                 }
```

---

## 🔸Usage

  Two default hooks are defined [here](../admin_cohort/tools/hooks.py) that make a calls to an external identity server and 
  **requiring** the following environment variables to be set:

  | Variable                   | Description                 | Default Value   | Required ? |
  |----------------------------|-----------------------------|-----------------|------------|
  | IDENTITY_SERVER_URL        | Ex: https://id-server.com   |                 | `yes`      |
  | IDENTITY_SERVER_AUTH_TOKEN | The identity server API key |                 | `yes`      |


