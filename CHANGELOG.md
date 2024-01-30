#  (2024-01-18)


### Bug Fixes

* add env var for tests ([aa85c3e](https://github.com/aphp/Cohort360-Back-end/commit/aa85c3e26b7738d7bad6c8a855d9804d2732b90e))
* adjust user permission to allow users to read their own data ([da347a2](https://github.com/aphp/Cohort360-Back-end/commit/da347a2c3936a9fb98a167bf8f4aa0d265bf9327))
* **auth:** remove unnecessary logging on token refresh failure ([9a3cf0f](https://github.com/aphp/Cohort360-Back-end/commit/9a3cf0f83b8afdc05d4271b8567ce8a0486a019e))
* **cohort:** count requests ([f156798](https://github.com/aphp/Cohort360-Back-end/commit/f15679875b5d2a21934eb73e064f619f909bcc98))
* **cohort:** format cohort ids for rights checking ([7b44ac2](https://github.com/aphp/Cohort360-Back-end/commit/7b44ac2d6c524dd548a58d411b29c940b7305308))
* **crb:** add right check in crb [#2401](https://github.com/aphp/Cohort360-Back-end/issues/2401) ([#297](https://github.com/aphp/Cohort360-Back-end/issues/297)) ([d87310a](https://github.com/aphp/Cohort360-Back-end/commit/d87310a78a675389ba60a31cc1d9698f50a23f28))
* **CRB:** hotfix 3.16.14 crb rights check ([#300](https://github.com/aphp/Cohort360-Back-end/issues/300)) ([0f2ba21](https://github.com/aphp/Cohort360-Back-end/commit/0f2ba219ba915da8a39258de35a428b2243e7189))
* **emailing for exports:** hotfix 3.16.3 ([#288](https://github.com/aphp/Cohort360-Back-end/issues/288)) ([168f8e4](https://github.com/aphp/Cohort360-Back-end/commit/168f8e4ccdf922442d7b1979bbec901e65991cad))
* **exports new flow:** resolve conflicts after merge exports new flow v1 PR ([bf4d4a4](https://github.com/aphp/Cohort360-Back-end/commit/bf4d4a4dbb97612554356b800689281a921d701e))
* **exports:** hotfix 3.17.3 ([#316](https://github.com/aphp/Cohort360-Back-end/issues/316)) ([2f62c09](https://github.com/aphp/Cohort360-Back-end/commit/2f62c09adb0cb3ad485ebec9c9ddd6bfd22ec2c5))
* **exports:** hotfix 3.17.3 fix typo in attribute name ([#315](https://github.com/aphp/Cohort360-Back-end/issues/315)) ([b386e13](https://github.com/aphp/Cohort360-Back-end/commit/b386e13e8727efa5b68ea6fe5c1141d5552e5052))
* **exports:** hotfix 3.17.4 to remove unused call to infra api ([#317](https://github.com/aphp/Cohort360-Back-end/issues/317)) ([c7bf565](https://github.com/aphp/Cohort360-Back-end/commit/c7bf565d9367ff0905c4ca96bb85ead684985f1a))
* **exports:** hotfix 3.17.5 remove check user unix account ([#318](https://github.com/aphp/Cohort360-Back-end/issues/318)) ([ddbfa0a](https://github.com/aphp/Cohort360-Back-end/commit/ddbfa0abc31997732e1e5b2b2117b4528476bc8c))
* **exports:** new statuses ([bfa0a2d](https://github.com/aphp/Cohort360-Back-end/commit/bfa0a2d91c34ee813ced2b05a048adfb51cace16))
* **exports:** use new statuses from Infra API ([#309](https://github.com/aphp/Cohort360-Back-end/issues/309)) ([7998384](https://github.com/aphp/Cohort360-Back-end/commit/7998384e094f7e93d5f3fef7331a37fc56494ac0))
* **feasibility studies:** add specific logger ([d1a9cc3](https://github.com/aphp/Cohort360-Back-end/commit/d1a9cc3f8679ec083e16ba9d646fb811df9fc5e6))
* **feasibility studies:** format request input ([1346667](https://github.com/aphp/Cohort360-Back-end/commit/134666797a9126af2723a51548cab947b540d15f))
* **feasibility studies:** properly chain tasks ([5cdfb70](https://github.com/aphp/Cohort360-Back-end/commit/5cdfb70232fa655313859766b8ab02786a19e30a))
* **feasibility studies:** properly set callbackPath in the SJS payload ([8253492](https://github.com/aphp/Cohort360-Back-end/commit/8253492d8e589cf2faa5ac1c141484824aab7ccd))
* **feasibility studies:** report download and notify on success and on error ([654df69](https://github.com/aphp/Cohort360-Back-end/commit/654df69257777426882ff59edcf7bb22059295c5))
* **feasibility_studies:** fix error on creation ([170d29d](https://github.com/aphp/Cohort360-Back-end/commit/170d29d721b9223260a02f0364b25c6ea097d267))
* **fhir filters:** add conditional unique constraint ([dcfb166](https://github.com/aphp/Cohort360-Back-end/commit/dcfb166c69219e0dd180ac8d9a79b63230d132c0))
* **fhir filters:** allow to delete filters ([027740a](https://github.com/aphp/Cohort360-Back-end/commit/027740aa4a4a5918e2360a19de86ec3e7f84f018))
* **fhir filters:** alter uniqueness rule and remove cache ([780686d](https://github.com/aphp/Cohort360-Back-end/commit/780686d7798fe0b407997c5f591b6f3687caa0e4))
* **fhir filters:** fix serializer and tests ([4421dfb](https://github.com/aphp/Cohort360-Back-end/commit/4421dfb52f3e3dcc3ac43e0e967fcc4e99b5d24c))
* **fhir filters:** get owner_id from request ([e4f4349](https://github.com/aphp/Cohort360-Back-end/commit/e4f43493a7a375b8cd01cfc5bad2da9f9caf4bb0))
* **fhir filters:** linter ([3585afb](https://github.com/aphp/Cohort360-Back-end/commit/3585afb84b3ff7d1366c3c0d9194cbbbc0a86590))
* **fhir filters:** make FhirFilter objects user restricted only ([4343127](https://github.com/aphp/Cohort360-Back-end/commit/4343127c6cadfc58be79bbd646a425e41e8c4049))
* **fhir filters:** typo in tests ([36766f5](https://github.com/aphp/Cohort360-Back-end/commit/36766f5669596927c876c681aab0204031cd095b))
* filter accesses on perimeters for user and deny deleting a used role ([587e8c5](https://github.com/aphp/Cohort360-Back-end/commit/587e8c584eff5248e3731e1101888a43b35d68f5))
* get user data rights ([621177b](https://github.com/aphp/Cohort360-Back-end/commit/621177bafedf3ac41bd5c8de7f62e56aacb401d1))
* get user data rights on perimeters ([84e9943](https://github.com/aphp/Cohort360-Back-end/commit/84e994387df7c9b83c342dcf6e1e3fc743a4e6ae))
* hotfix 3.16.6 for queries updater ([#292](https://github.com/aphp/Cohort360-Back-end/issues/292)) ([07d4ae7](https://github.com/aphp/Cohort360-Back-end/commit/07d4ae7e3c8250a7fd8446539ba014de7b344ee3))
* hotfix 3.16.7 for computing user rights ([#293](https://github.com/aphp/Cohort360-Back-end/issues/293)) ([bcf50af](https://github.com/aphp/Cohort360-Back-end/commit/bcf50afd884b14e30f3b0c3201093a4b317a139c))
* hotfix 3.16.8 for Exports permissions ([#294](https://github.com/aphp/Cohort360-Back-end/issues/294)) ([fbed005](https://github.com/aphp/Cohort360-Back-end/commit/fbed005deb0e9748b02fdae7f7f1744e6ef79f3a))
* hotfix 3.17.1 ([#310](https://github.com/aphp/Cohort360-Back-end/issues/310)) ([13d5d3b](https://github.com/aphp/Cohort360-Back-end/commit/13d5d3b920cecfc0212f7f28d8371cfabf031136))
* hotfix 3.17.2 for right check regression for FHIR ([#313](https://github.com/aphp/Cohort360-Back-end/issues/313)) ([c6a6dfb](https://github.com/aphp/Cohort360-Back-end/commit/c6a6dfb0a978728f741c643ede6cf31e7bd37176))
* improve exports v1 ([#308](https://github.com/aphp/Cohort360-Back-end/issues/308)) ([d04707f](https://github.com/aphp/Cohort360-Back-end/commit/d04707fb9ccdbfcdcf89b94b2343de242859ffc5))
* log request data and params ([7f09e1a](https://github.com/aphp/Cohort360-Back-end/commit/7f09e1ac31158bff5b5c6fa59caaea1fd3252aea))
* manage invalid token errors ([6ee96d7](https://github.com/aphp/Cohort360-Back-end/commit/6ee96d7ce35726827d640446ba832626dc87fcf5))
* manage invalid token errors ([28e9902](https://github.com/aphp/Cohort360-Back-end/commit/28e9902d403cf9422a520ba87027e19d732ed5c3))
* **migrationscript:** correct mapping script ([d171d5e](https://github.com/aphp/Cohort360-Back-end/commit/d171d5ec5f699ef30c9c848fb1d87b113e60d5ae))
* parse fhir_group_ids to get cohort rights ([d565ca9](https://github.com/aphp/Cohort360-Back-end/commit/d565ca9efd3a6d46a87fafc6723c12993d81e486))
* pass perimeters ids instead of queryset to check rights ([e8f15d1](https://github.com/aphp/Cohort360-Back-end/commit/e8f15d13c4a71c7cacee02645d11ee6a5ad5cbf5))
* perimeters daily update task ([2ab5cb7](https://github.com/aphp/Cohort360-Back-end/commit/2ab5cb7d803c736ed6ba963e0d32fcde1dd76e6b))
* **perimeters:** correct cohort_ids type ([#302](https://github.com/aphp/Cohort360-Back-end/issues/302)) ([4c12b5d](https://github.com/aphp/Cohort360-Back-end/commit/4c12b5dfaca8919bc3c53c0f994f4a2f5d19a2ad))
* psycopg package name in requirements.txt ([323b85a](https://github.com/aphp/Cohort360-Back-end/commit/323b85a4418fa9e641f96640681b0438211e9ca1))
* **querymigration:** fix code translation + add new v1.4.1 script ([#291](https://github.com/aphp/Cohort360-Back-end/issues/291)) ([3358889](https://github.com/aphp/Cohort360-Back-end/commit/3358889f0450caea6bf73ea353cf5022b3560160))
* **queryupgrade:** fix sql + add previous version limit to upgrade + versions recap ([#287](https://github.com/aphp/Cohort360-Back-end/issues/287)) ([88f431e](https://github.com/aphp/Cohort360-Back-end/commit/88f431ec95448889edcae4835be9d2149b35867e))
* raise raw exception on login error via OIDC ([06c9cca](https://github.com/aphp/Cohort360-Back-end/commit/06c9ccaae2bda91f22bd9e0f28e1f4f0d3f4647b))
* raise specific exception ([fa78c9b](https://github.com/aphp/Cohort360-Back-end/commit/fa78c9b63f9932df379747b85e146e669eb794c3))
* **release notes:** sort data in response, allow patch ([becd603](https://github.com/aphp/Cohort360-Back-end/commit/becd603e8f625fb22e15cfded2abe72eab8772a4))
* remove unique rights combination constraint ([10e0bc5](https://github.com/aphp/Cohort360-Back-end/commit/10e0bc541abf932aadcb753454cbd06e0a4dd3cc))
* **requests logs:** for FhirFilters ([fce53c9](https://github.com/aphp/Cohort360-Back-end/commit/fce53c9b3ad91705abd635d2ac9d34db30b13d48))
* rm unused imports ([2f6da6e](https://github.com/aphp/Cohort360-Back-end/commit/2f6da6e7f367d020259c92a8288b3e5dc18443ee))
* rqs version incrementing ([67ef4c8](https://github.com/aphp/Cohort360-Back-end/commit/67ef4c8e905b71a1ad79c2c5bf4d90f98d0c1e79))
* set main to v3.17.0-SNAPSHOT ([8d58391](https://github.com/aphp/Cohort360-Back-end/commit/8d5839141e2385753d56f7cfc740fe65faaeda53))
* spark job request with callback path ([#311](https://github.com/aphp/Cohort360-Back-end/issues/311)) ([7825a75](https://github.com/aphp/Cohort360-Back-end/commit/7825a7525863a0f714d7a999fb7c91280be18cb2))
* update export email template ([e82a6e3](https://github.com/aphp/Cohort360-Back-end/commit/e82a6e37e727cfd02dd0588a13791cc413cff7a3))


### Features

* **accesses:** include link to accesses managers list in the email notification ([d99d406](https://github.com/aphp/Cohort360-Back-end/commit/d99d40600b7089447ef53effdd05c825df75f654))
* add feasibility studies ([#305](https://github.com/aphp/Cohort360-Back-end/issues/305)) ([5dab6fb](https://github.com/aphp/Cohort360-Back-end/commit/5dab6fb78925907c2531f6a9e0431d6f66e990cc))
* add new exports flow v1 ([#273](https://github.com/aphp/Cohort360-Back-end/issues/273)) ([5c5c318](https://github.com/aphp/Cohort360-Back-end/commit/5c5c318d0a5cb7de8d84249f7ba1552d49e8dd17))
* **cohortrequester:** add upgrade script for atih code conversion ([#296](https://github.com/aphp/Cohort360-Back-end/issues/296)) ([1504b7a](https://github.com/aphp/Cohort360-Back-end/commit/1504b7a8e192717157f70eea3f13f1b223921d79))
* **crb:** add new imagingStudy resource type ([#290](https://github.com/aphp/Cohort360-Back-end/issues/290)) ([640f8e4](https://github.com/aphp/Cohort360-Back-end/commit/640f8e4df84ca8dcc39e3bb8ab6680968b774992))
* **Fhir filters:** delete multiple filters ([bd981cd](https://github.com/aphp/Cohort360-Back-end/commit/bd981cd6a0e3f6c7ecfdd510456ae3d64b3e074a))
* **fhir filters:** get filters by user id and resource ([#307](https://github.com/aphp/Cohort360-Back-end/issues/307)) ([f7c0fef](https://github.com/aphp/Cohort360-Back-end/commit/f7c0fef34e444319469409d58c68a59afbfdef68))
* log HTTP requests ([#282](https://github.com/aphp/Cohort360-Back-end/issues/282)) ([7e66f83](https://github.com/aphp/Cohort360-Back-end/commit/7e66f83a70f19e82e928f54293bd4617a03f9a7b))
* upgrade Django ([#306](https://github.com/aphp/Cohort360-Back-end/issues/306)) ([ad0389c](https://github.com/aphp/Cohort360-Back-end/commit/ad0389cf93c76938a20719a18dc169ec56fc3173))
* use token to activate maintenance for rollout ([#298](https://github.com/aphp/Cohort360-Back-end/issues/298)) ([7168448](https://github.com/aphp/Cohort360-Back-end/commit/71684488e5e2f7020fa4f24c62635bdd9c170970))



#  (2024-01-09)


### Bug Fixes

* add env var for tests ([aa85c3e](https://github.com/aphp/Cohort360-Back-end/commit/aa85c3e26b7738d7bad6c8a855d9804d2732b90e))
* **exports:** new statuses ([bfa0a2d](https://github.com/aphp/Cohort360-Back-end/commit/bfa0a2d91c34ee813ced2b05a048adfb51cace16))
* **exports:** use new statuses from Infra API ([#309](https://github.com/aphp/Cohort360-Back-end/issues/309)) ([7998384](https://github.com/aphp/Cohort360-Back-end/commit/7998384e094f7e93d5f3fef7331a37fc56494ac0))
* filter accesses on perimeters for user and deny deleting a used role ([587e8c5](https://github.com/aphp/Cohort360-Back-end/commit/587e8c584eff5248e3731e1101888a43b35d68f5))
* get user data rights ([621177b](https://github.com/aphp/Cohort360-Back-end/commit/621177bafedf3ac41bd5c8de7f62e56aacb401d1))
* get user data rights on perimeters ([84e9943](https://github.com/aphp/Cohort360-Back-end/commit/84e994387df7c9b83c342dcf6e1e3fc743a4e6ae))
* hotfix 3.17.1 ([#310](https://github.com/aphp/Cohort360-Back-end/issues/310)) ([13d5d3b](https://github.com/aphp/Cohort360-Back-end/commit/13d5d3b920cecfc0212f7f28d8371cfabf031136))
* improve exports v1 ([#308](https://github.com/aphp/Cohort360-Back-end/issues/308)) ([d04707f](https://github.com/aphp/Cohort360-Back-end/commit/d04707fb9ccdbfcdcf89b94b2343de242859ffc5))
* log request data and params ([7f09e1a](https://github.com/aphp/Cohort360-Back-end/commit/7f09e1ac31158bff5b5c6fa59caaea1fd3252aea))
* parse fhir_group_ids to get cohort rights ([d565ca9](https://github.com/aphp/Cohort360-Back-end/commit/d565ca9efd3a6d46a87fafc6723c12993d81e486))
* pass perimeters ids instead of queryset to check rights ([e8f15d1](https://github.com/aphp/Cohort360-Back-end/commit/e8f15d13c4a71c7cacee02645d11ee6a5ad5cbf5))
* perimeters daily update task ([2ab5cb7](https://github.com/aphp/Cohort360-Back-end/commit/2ab5cb7d803c736ed6ba963e0d32fcde1dd76e6b))
* **perimeters:** correct cohort_ids type ([#302](https://github.com/aphp/Cohort360-Back-end/issues/302)) ([4c12b5d](https://github.com/aphp/Cohort360-Back-end/commit/4c12b5dfaca8919bc3c53c0f994f4a2f5d19a2ad))
* psycopg package name in requirements.txt ([323b85a](https://github.com/aphp/Cohort360-Back-end/commit/323b85a4418fa9e641f96640681b0438211e9ca1))
* remove unique rights combination constraint ([10e0bc5](https://github.com/aphp/Cohort360-Back-end/commit/10e0bc541abf932aadcb753454cbd06e0a4dd3cc))
* rm unused imports ([2f6da6e](https://github.com/aphp/Cohort360-Back-end/commit/2f6da6e7f367d020259c92a8288b3e5dc18443ee))
* spark job request with callback path ([#311](https://github.com/aphp/Cohort360-Back-end/issues/311)) ([7825a75](https://github.com/aphp/Cohort360-Back-end/commit/7825a7525863a0f714d7a999fb7c91280be18cb2))


### Features

* add feasibility studies ([#305](https://github.com/aphp/Cohort360-Back-end/issues/305)) ([5dab6fb](https://github.com/aphp/Cohort360-Back-end/commit/5dab6fb78925907c2531f6a9e0431d6f66e990cc))
* **fhir filters:** get filters by user id and resource ([#307](https://github.com/aphp/Cohort360-Back-end/issues/307)) ([f7c0fef](https://github.com/aphp/Cohort360-Back-end/commit/f7c0fef34e444319469409d58c68a59afbfdef68))
* upgrade Django ([#306](https://github.com/aphp/Cohort360-Back-end/issues/306)) ([ad0389c](https://github.com/aphp/Cohort360-Back-end/commit/ad0389cf93c76938a20719a18dc169ec56fc3173))



## [3.16.15](https://github.com/aphp/Cohort360-Back-end/compare/3.16.0...3.16.15) (2023-12-12)


### Bug Fixes

* adjust user permission to allow users to read their own data ([da347a2](https://github.com/aphp/Cohort360-Back-end/commit/da347a2c3936a9fb98a167bf8f4aa0d265bf9327))
* **cohort:** count requests ([f156798](https://github.com/aphp/Cohort360-Back-end/commit/f15679875b5d2a21934eb73e064f619f909bcc98))
* **cohort:** format cohort ids for rights checking ([7b44ac2](https://github.com/aphp/Cohort360-Back-end/commit/7b44ac2d6c524dd548a58d411b29c940b7305308))
* **crb:** add right check in crb [#2401](https://github.com/aphp/Cohort360-Back-end/issues/2401) ([#297](https://github.com/aphp/Cohort360-Back-end/issues/297)) ([d87310a](https://github.com/aphp/Cohort360-Back-end/commit/d87310a78a675389ba60a31cc1d9698f50a23f28))
* **CRB:** hotfix 3.16.14 crb rights check ([#300](https://github.com/aphp/Cohort360-Back-end/issues/300)) ([0f2ba21](https://github.com/aphp/Cohort360-Back-end/commit/0f2ba219ba915da8a39258de35a428b2243e7189))
* **emailing for exports:** hotfix 3.16.3 ([#288](https://github.com/aphp/Cohort360-Back-end/issues/288)) ([168f8e4](https://github.com/aphp/Cohort360-Back-end/commit/168f8e4ccdf922442d7b1979bbec901e65991cad))
* **exports new flow:** resolve conflicts after merge exports new flow v1 PR ([bf4d4a4](https://github.com/aphp/Cohort360-Back-end/commit/bf4d4a4dbb97612554356b800689281a921d701e))
* **fhir filters:** add conditional unique constraint ([dcfb166](https://github.com/aphp/Cohort360-Back-end/commit/dcfb166c69219e0dd180ac8d9a79b63230d132c0))
* **fhir filters:** allow to delete filters ([027740a](https://github.com/aphp/Cohort360-Back-end/commit/027740aa4a4a5918e2360a19de86ec3e7f84f018))
* **fhir filters:** alter uniqueness rule and remove cache ([780686d](https://github.com/aphp/Cohort360-Back-end/commit/780686d7798fe0b407997c5f591b6f3687caa0e4))
* **fhir filters:** fix serializer and tests ([4421dfb](https://github.com/aphp/Cohort360-Back-end/commit/4421dfb52f3e3dcc3ac43e0e967fcc4e99b5d24c))
* **fhir filters:** get owner_id from request ([e4f4349](https://github.com/aphp/Cohort360-Back-end/commit/e4f43493a7a375b8cd01cfc5bad2da9f9caf4bb0))
* **fhir filters:** linter ([3585afb](https://github.com/aphp/Cohort360-Back-end/commit/3585afb84b3ff7d1366c3c0d9194cbbbc0a86590))
* **fhir filters:** make FhirFilter objects user restricted only ([4343127](https://github.com/aphp/Cohort360-Back-end/commit/4343127c6cadfc58be79bbd646a425e41e8c4049))
* **fhir filters:** typo in tests ([36766f5](https://github.com/aphp/Cohort360-Back-end/commit/36766f5669596927c876c681aab0204031cd095b))
* hotfix 3.16.6 for queries updater ([#292](https://github.com/aphp/Cohort360-Back-end/issues/292)) ([07d4ae7](https://github.com/aphp/Cohort360-Back-end/commit/07d4ae7e3c8250a7fd8446539ba014de7b344ee3))
* hotfix 3.16.7 for computing user rights ([#293](https://github.com/aphp/Cohort360-Back-end/issues/293)) ([bcf50af](https://github.com/aphp/Cohort360-Back-end/commit/bcf50afd884b14e30f3b0c3201093a4b317a139c))
* hotfix 3.16.8 for Exports permissions ([#294](https://github.com/aphp/Cohort360-Back-end/issues/294)) ([fbed005](https://github.com/aphp/Cohort360-Back-end/commit/fbed005deb0e9748b02fdae7f7f1744e6ef79f3a))
* manage invalid token errors ([6ee96d7](https://github.com/aphp/Cohort360-Back-end/commit/6ee96d7ce35726827d640446ba832626dc87fcf5))
* manage invalid token errors ([28e9902](https://github.com/aphp/Cohort360-Back-end/commit/28e9902d403cf9422a520ba87027e19d732ed5c3))
* **migrationscript:** correct mapping script ([d171d5e](https://github.com/aphp/Cohort360-Back-end/commit/d171d5ec5f699ef30c9c848fb1d87b113e60d5ae))
* **querymigration:** fix code translation + add new v1.4.1 script ([#291](https://github.com/aphp/Cohort360-Back-end/issues/291)) ([3358889](https://github.com/aphp/Cohort360-Back-end/commit/3358889f0450caea6bf73ea353cf5022b3560160))
* **queryupgrade:** fix sql + add previous version limit to upgrade + versions recap ([#287](https://github.com/aphp/Cohort360-Back-end/issues/287)) ([88f431e](https://github.com/aphp/Cohort360-Back-end/commit/88f431ec95448889edcae4835be9d2149b35867e))
* raise specific exception ([fa78c9b](https://github.com/aphp/Cohort360-Back-end/commit/fa78c9b63f9932df379747b85e146e669eb794c3))
* **release notes:** sort data in response, allow patch ([becd603](https://github.com/aphp/Cohort360-Back-end/commit/becd603e8f625fb22e15cfded2abe72eab8772a4))
* **requests logs:** for FhirFilters ([fce53c9](https://github.com/aphp/Cohort360-Back-end/commit/fce53c9b3ad91705abd635d2ac9d34db30b13d48))
* rqs version incrementing ([67ef4c8](https://github.com/aphp/Cohort360-Back-end/commit/67ef4c8e905b71a1ad79c2c5bf4d90f98d0c1e79))
* set main to v3.17.0-SNAPSHOT ([8d58391](https://github.com/aphp/Cohort360-Back-end/commit/8d5839141e2385753d56f7cfc740fe65faaeda53))
* update export email template ([e82a6e3](https://github.com/aphp/Cohort360-Back-end/commit/e82a6e37e727cfd02dd0588a13791cc413cff7a3))


### Features

* add new exports flow v1 ([#273](https://github.com/aphp/Cohort360-Back-end/issues/273)) ([5c5c318](https://github.com/aphp/Cohort360-Back-end/commit/5c5c318d0a5cb7de8d84249f7ba1552d49e8dd17))
* **cohortrequester:** add upgrade script for atih code conversion ([#296](https://github.com/aphp/Cohort360-Back-end/issues/296)) ([1504b7a](https://github.com/aphp/Cohort360-Back-end/commit/1504b7a8e192717157f70eea3f13f1b223921d79))
* **crb:** add new imagingStudy resource type ([#290](https://github.com/aphp/Cohort360-Back-end/issues/290)) ([640f8e4](https://github.com/aphp/Cohort360-Back-end/commit/640f8e4df84ca8dcc39e3bb8ab6680968b774992))
* **Fhir filters:** delete multiple filters ([bd981cd](https://github.com/aphp/Cohort360-Back-end/commit/bd981cd6a0e3f6c7ecfdd510456ae3d64b3e074a))
* log HTTP requests ([#282](https://github.com/aphp/Cohort360-Back-end/issues/282)) ([7e66f83](https://github.com/aphp/Cohort360-Back-end/commit/7e66f83a70f19e82e928f54293bd4617a03f9a7b))
* use token to activate maintenance for rollout ([#298](https://github.com/aphp/Cohort360-Back-end/issues/298)) ([7168448](https://github.com/aphp/Cohort360-Back-end/commit/71684488e5e2f7020fa4f24c62635bdd9c170970))



# [3.16.0](https://github.com/aphp/Cohort360-Back-end/compare/3.15.0...3.16.0) (2023-10-13)


### Bug Fixes

*  review permissions and hide urls in the DRF api view ([#272](https://github.com/aphp/Cohort360-Back-end/issues/272)) ([957db3d](https://github.com/aphp/Cohort360-Back-end/commit/957db3d203c080b0d329eb5103f55250e29bc627))
* add migration for old release notes ([18bc596](https://github.com/aphp/Cohort360-Back-end/commit/18bc596595419b04fa5ade4611a33b231c26e618))
* alter release notes migration ([dc163b2](https://github.com/aphp/Cohort360-Back-end/commit/dc163b2c537b9c52898faf9736f9664dfa2009f4))
* attach logo to email signature ([49cd711](https://github.com/aphp/Cohort360-Back-end/commit/49cd7118ed3eb192047da30b078b70c9a823de85))
* count user on perimeters ([#269](https://github.com/aphp/Cohort360-Back-end/issues/269)) ([8b7eba6](https://github.com/aphp/Cohort360-Back-end/commit/8b7eba6dddf6139ef089f8514454dd9c89abfaf4))
* count users on perimeters ([#268](https://github.com/aphp/Cohort360-Back-end/issues/268)) ([a159e8c](https://github.com/aphp/Cohort360-Back-end/commit/a159e8ccc2b6d248732c8f89c0750431da751543))
* **crb:** correct sjs replacements ([7e02500](https://github.com/aphp/Cohort360-Back-end/commit/7e02500391eee77314967af5be9d92bebc60f1ae))
* **crb:** ipp list resource name ([#283](https://github.com/aphp/Cohort360-Back-end/issues/283)) ([73e80dd](https://github.com/aphp/Cohort360-Back-end/commit/73e80dd23bec3968ba022e06dd354662825e2417))
* **crb:** optional fields for temporal constraints ([826e811](https://github.com/aphp/Cohort360-Back-end/commit/826e8115dee8a9381a7d07d10b8d5d1b7278e26e))
* **crb:** rename serialized model ([#280](https://github.com/aphp/Cohort360-Back-end/issues/280)) ([7e66012](https://github.com/aphp/Cohort360-Back-end/commit/7e660122cc762b3c63375dee0ce5aa3e3f9a791f))
* exports bug fix and emails refactor ([#274](https://github.com/aphp/Cohort360-Back-end/issues/274)) ([2e54e06](https://github.com/aphp/Cohort360-Back-end/commit/2e54e065d2d347aefb6d66e876291f6552dd7c96))
* extend try catch in crb process + add optional fields to query model ([78481a6](https://github.com/aphp/Cohort360-Back-end/commit/78481a64805459de760aaa934e7d23009e5b177c))
* fix conflicts after merge ([f131fbe](https://github.com/aphp/Cohort360-Back-end/commit/f131fbec109c4fbff626d28c6348a4031f8e20b5))
* fix migration dependency ([75fcd51](https://github.com/aphp/Cohort360-Back-end/commit/75fcd51e19c581b9bc88f56ca4bc2aae31cd13fc))
* hotfix_3.15.3 accesses on perimeters ([#270](https://github.com/aphp/Cohort360-Back-end/issues/270)) ([6e82147](https://github.com/aphp/Cohort360-Back-end/commit/6e82147a8431bac7bff3e44f84f2d5d02c175a2a))
* manage downloading old csv exports ([#277](https://github.com/aphp/Cohort360-Back-end/issues/277)) ([b791532](https://github.com/aphp/Cohort360-Back-end/commit/b791532d37e91d09b2fcfb58de18858bf323e327))
* move patches to scripts ([054318f](https://github.com/aphp/Cohort360-Back-end/commit/054318f3801304d50c855f87b27bf8db68e3818a))
* permissions for exports new  views ([#267](https://github.com/aphp/Cohort360-Back-end/issues/267)) ([605a3d5](https://github.com/aphp/Cohort360-Back-end/commit/605a3d53e7855c51e33a29082ce32f4ee5cb1fde))
* **requestmigration:** add new param mappings ([#284](https://github.com/aphp/Cohort360-Back-end/issues/284)) ([cb636d2](https://github.com/aphp/Cohort360-Back-end/commit/cb636d2a4f77633fefd34b1c3a2c3035026d9dd9))
* **serializedquery:** correct field mapping + add medication new mapping ([#281](https://github.com/aphp/Cohort360-Back-end/issues/281)) ([8ead2cf](https://github.com/aphp/Cohort360-Back-end/commit/8ead2cfcbc918f1c6ab596edee8836712aade7d5))
* silently log JWT token errors ([f5aa02c](https://github.com/aphp/Cohort360-Back-end/commit/f5aa02ca3b5f8766c1dc1a21837f61c563c47ea3))
* small changes after merge ([c7d4d28](https://github.com/aphp/Cohort360-Back-end/commit/c7d4d2878e52a3f611aedc67cb3f008eabd61b69))
* upgrade to Django v4.1.11 ([208839c](https://github.com/aphp/Cohort360-Back-end/commit/208839c688b3c4fd3d02de0a4507c271e4988c40))


### Features

* add console handler for logs in local env, dev and qua ([6b3b383](https://github.com/aphp/Cohort360-Back-end/commit/6b3b383b8bded6a1efcd38a190db0030a42249ca))
* add views to manage cache ([#262](https://github.com/aphp/Cohort360-Back-end/issues/262)) ([3ba7691](https://github.com/aphp/Cohort360-Back-end/commit/3ba7691f17fa1aaf694175ff6fa48059a10ace82))
* **cohort:** add cohort request builder service ([#263](https://github.com/aphp/Cohort360-Back-end/issues/263)) ([3aa7f25](https://github.com/aphp/Cohort360-Back-end/commit/3aa7f251bd54ad7e5442523413dbcbebcbe9a685))
* **cohort:** add cohort request builder service ([#263](https://github.com/aphp/Cohort360-Back-end/issues/263)) ([d42c7ed](https://github.com/aphp/Cohort360-Back-end/commit/d42c7ed460a77946b6f8b3fb79c079c29378606a))
* **cohort:** add new migration script for serialized queries in 1.4.0 ([#271](https://github.com/aphp/Cohort360-Back-end/issues/271)) ([a3f6678](https://github.com/aphp/Cohort360-Back-end/commit/a3f6678915df44c125aad55e93732783ff943ff2))
* **crb:** add real fhir query test ([#285](https://github.com/aphp/Cohort360-Back-end/issues/285)) ([dd63f34](https://github.com/aphp/Cohort360-Back-end/commit/dd63f344973e826bd7292c75ddc24926a8e6fcf8))
* **exports:** add new models ([#266](https://github.com/aphp/Cohort360-Back-end/issues/266)) ([1537781](https://github.com/aphp/Cohort360-Back-end/commit/153778171bd125583084e2eb80a06d93c5456429))
* manage release notes and news ([#279](https://github.com/aphp/Cohort360-Back-end/issues/279)) ([3a0baff](https://github.com/aphp/Cohort360-Back-end/commit/3a0baff98c75302829f3264201eff750e211eb70))



# [3.15.0](https://github.com/aphp/Cohort360-Back-end/compare/3.14.1...3.15.0) (2023-09-05)


### Bug Fixes

* change fields mapping with ID checker server ([#252](https://github.com/aphp/Cohort360-Back-end/issues/252)) ([ed47e26](https://github.com/aphp/Cohort360-Back-end/commit/ed47e26e5b8a52e7c53eb8112df3629aff285962))



## [3.14.1](https://github.com/aphp/Cohort360-Back-end/compare/3.14.0...3.14.1) (2023-08-09)


### Bug Fixes

* add a null check before adding trace id to headers ([b38d80c](https://github.com/aphp/Cohort360-Back-end/commit/b38d80cd0779c705199e28885bcd3e5118514ea2))
* add default values to variables in test env ([30c2d00](https://github.com/aphp/Cohort360-Back-end/commit/30c2d002e7222b36c91b9bae7d8b05acf7d50bbe))
* add migration dependency ([08758f9](https://github.com/aphp/Cohort360-Back-end/commit/08758f92908f58d8f806bd568603026400d83513))
* add missing dependency ([54a9eca](https://github.com/aphp/Cohort360-Back-end/commit/54a9ecaae15f06cce2fc6fd66cbdde58081fa82e))
* adjust responses on checking profiles ([9d84825](https://github.com/aphp/Cohort360-Back-end/commit/9d84825f31ff2a7550d73afbdd77738a2d5d8fda))
* **cache:** include request params and path in keys ([#229](https://github.com/aphp/Cohort360-Back-end/issues/229)) ([0d40407](https://github.com/aphp/Cohort360-Back-end/commit/0d40407a73958510f0471605ed9036087527e1cf))
* **cache:** include request's path in cache key ([f76a24f](https://github.com/aphp/Cohort360-Back-end/commit/f76a24f55d3e301a8ad471fbf570c4272c4d5760))
* **cache:** invalidate cache on request sharing ([29371db](https://github.com/aphp/Cohort360-Back-end/commit/29371dbc8b0a7fe77eb996b8cd1e6ba6179a98bb))
* **exports:** enable limit on cohorts list for exports ([#220](https://github.com/aphp/Cohort360-Back-end/issues/220)) ([e7b5caf](https://github.com/aphp/Cohort360-Back-end/commit/e7b5cafd2be94ded71b485f7120b4f6c47e5a66c))
* **exports:** properly pass InfraAPI auth token ([#216](https://github.com/aphp/Cohort360-Back-end/issues/216)) ([e2c763a](https://github.com/aphp/Cohort360-Back-end/commit/e2c763a46d0c186bf1b604c94854d60e9d45c5bb))
* hotfix 3.13.7 notify admins about errors ([#236](https://github.com/aphp/Cohort360-Back-end/issues/236)) ([293b3be](https://github.com/aphp/Cohort360-Back-end/commit/293b3be96a3f6ee954d5007ce55ab37c2116cc2a))
* hotfix 3.13.8 serve static files ([#242](https://github.com/aphp/Cohort360-Back-end/issues/242)) ([6ef7408](https://github.com/aphp/Cohort360-Back-end/commit/6ef74082834e2dd30f46d5067ef83dd6cc83eb32))
* hotfix 3.13.9 decode jwt per issuer ([#245](https://github.com/aphp/Cohort360-Back-end/issues/245)) ([8252b7d](https://github.com/aphp/Cohort360-Back-end/commit/8252b7d546451ebf501083dc44ecc48bcd5559cc))
* hotfix 3.14.1 add cohort name on email subject for export requests ([#247](https://github.com/aphp/Cohort360-Back-end/issues/247)) ([b178f82](https://github.com/aphp/Cohort360-Back-end/commit/b178f82bea3e1d58004ecad4a5ec9b52f2de9fc0))
* hotfix 3.14.1 cohort name in export email subject ([#248](https://github.com/aphp/Cohort360-Back-end/issues/248)) ([a48022a](https://github.com/aphp/Cohort360-Back-end/commit/a48022ad7ea8e7e71c2649a9a55fd20fabdbc4c3))
* hotfix 3.14.1 cohort name in export email subject ([#249](https://github.com/aphp/Cohort360-Back-end/issues/249)) ([124f9ba](https://github.com/aphp/Cohort360-Back-end/commit/124f9ba189e67b5e9662061229f95273119c7663))
* hotfix 3.14.1 cohort name in export email subject ([#250](https://github.com/aphp/Cohort360-Back-end/issues/250)) ([3d2897b](https://github.com/aphp/Cohort360-Back-end/commit/3d2897b694b9d040c61ba2d31eb836fe5e62f2dd))
* log instead of raise error on logout ([#231](https://github.com/aphp/Cohort360-Back-end/issues/231)) ([9951279](https://github.com/aphp/Cohort360-Back-end/commit/995127907795637c3a7b48296727aa2b8d65a445))
* **migration:** fix dependency ([36fa73e](https://github.com/aphp/Cohort360-Back-end/commit/36fa73e650752e30822e76c2bbf89c4054d74b82))
* **migration:** fix dependency ([619c0de](https://github.com/aphp/Cohort360-Back-end/commit/619c0de7a14e6ddc8d12d77676eb0d7cf7c905d2))
* **migration:** run Python instead of SQL ([a564033](https://github.com/aphp/Cohort360-Back-end/commit/a564033fea5a99a432819bde1672a2e95a6d4dea))
* portail patient OIDC auth ([#234](https://github.com/aphp/Cohort360-Back-end/issues/234)) ([8715bbc](https://github.com/aphp/Cohort360-Back-end/commit/8715bbc8179330ae46e357c62eac19761ab45aa0))
* reset cache on request sharing ([#225](https://github.com/aphp/Cohort360-Back-end/issues/225)) ([8e0130f](https://github.com/aphp/Cohort360-Back-end/commit/8e0130f67ecac602d4519a72ae04013ada43192f))
* set version 3.14.0-SNAPSHOT ([810dd69](https://github.com/aphp/Cohort360-Back-end/commit/810dd69d95f982df46bca2869e8afceecf18df6d))


### Features

* **Accesses:** add created_by and updated_by ([#223](https://github.com/aphp/Cohort360-Back-end/issues/223)) ([267d192](https://github.com/aphp/Cohort360-Back-end/commit/267d1920abeddd68ba54685537559ee3293d5ec2))
* **access:** set default minimum access duration to 2 years ([937243b](https://github.com/aphp/Cohort360-Back-end/commit/937243b2a25c4e9ca9ece6ca8b45dfad51e32dd4))
* add regex to manage service accounts usernames ([d802c1b](https://github.com/aphp/Cohort360-Back-end/commit/d802c1b5ad121c3882ccdb37a64a8e40897a153a))
* **exports:** add export name to mail subject ([#213](https://github.com/aphp/Cohort360-Back-end/issues/213)) ([d22d747](https://github.com/aphp/Cohort360-Back-end/commit/d22d747fdbe0443ee360fab45c85e2f37a90751e))
* **logging:** add trace id tag and set logging format to json ([#212](https://github.com/aphp/Cohort360-Back-end/issues/212)) ([9498d9b](https://github.com/aphp/Cohort360-Back-end/commit/9498d9b382b4b0273757a8b8ed13fbc27c527438))
* **request:** add param to optionnaly notify user when sharing request ([d3ecf3f](https://github.com/aphp/Cohort360-Back-end/commit/d3ecf3f954235d35f9a5a4f33e6a98e49ad13005))
* **requests:** send mail to receipients of shared requests ([#205](https://github.com/aphp/Cohort360-Back-end/issues/205)) ([e74d204](https://github.com/aphp/Cohort360-Back-end/commit/e74d204fe24d27540b7d421d898cf550b6ec34bd))



## [3.13.9](https://github.com/aphp/Cohort360-Back-end/compare/3.13.8...3.13.9) (2023-08-08)


### Bug Fixes

* hotfix_3.13.9 decode oidc tokens per issuer ([#244](https://github.com/aphp/Cohort360-Back-end/issues/244)) ([4b04a22](https://github.com/aphp/Cohort360-Back-end/commit/4b04a2228eda8413766442456fea8bcfdfad6aca))



## [3.13.8](https://github.com/aphp/Cohort360-Back-end/compare/3.13.7...3.13.8) (2023-08-03)


### Bug Fixes

* hotfix 3.13.8 serve static files ([#241](https://github.com/aphp/Cohort360-Back-end/issues/241)) ([2e14048](https://github.com/aphp/Cohort360-Back-end/commit/2e14048d1fdf4fecbcdaff268fa5f5ec6ca6ebb9))



## [3.13.7](https://github.com/aphp/Cohort360-Back-end/compare/3.13.6...3.13.7) (2023-08-02)


### Bug Fixes

* hotfix 3.13.7 notify admins about errors ([#235](https://github.com/aphp/Cohort360-Back-end/issues/235)) ([2e82e7a](https://github.com/aphp/Cohort360-Back-end/commit/2e82e7a6209aad5f47e1ae2b1163423f4962f3ab))



## [3.13.6](https://github.com/aphp/Cohort360-Back-end/compare/3.13.5...3.13.6) (2023-08-02)


### Bug Fixes

* hotfix 3.13.6 oidc auth with portail patients ([#233](https://github.com/aphp/Cohort360-Back-end/issues/233)) ([3696b9b](https://github.com/aphp/Cohort360-Back-end/commit/3696b9b7dbfe594ae6d2f79eef1ccbd80876d525))



## [3.13.5](https://github.com/aphp/Cohort360-Back-end/compare/3.13.4...3.13.5) (2023-08-01)


### Bug Fixes

* log instead of raise error on logout ([#230](https://github.com/aphp/Cohort360-Back-end/issues/230)) ([1924fe2](https://github.com/aphp/Cohort360-Back-end/commit/1924fe2eeacf917f45a6cde3925060d9a8cd8813))



## [3.13.4](https://github.com/aphp/Cohort360-Back-end/compare/3.13.3...3.13.4) (2023-07-27)


### Bug Fixes

* **cache:** include request params and path in keys ([#228](https://github.com/aphp/Cohort360-Back-end/issues/228)) ([299623f](https://github.com/aphp/Cohort360-Back-end/commit/299623f9f9cd17abaf20965e4d065b6074aed56d))
* **cache:** include request path in cache key ([#227](https://github.com/aphp/Cohort360-Back-end/issues/227)) ([59df542](https://github.com/aphp/Cohort360-Back-end/commit/59df5423e7b494ef9f35602ff6fb57765a386fb1))



## [3.13.3](https://github.com/aphp/Cohort360-Back-end/compare/3.13.2...3.13.3) (2023-07-26)


### Bug Fixes

* invalidate cache after bulk transactions ([#222](https://github.com/aphp/Cohort360-Back-end/issues/222)) ([4621199](https://github.com/aphp/Cohort360-Back-end/commit/4621199db0e550bf13ea385e2ebea97f733da80d))
* reset cache after sharing a request ([#226](https://github.com/aphp/Cohort360-Back-end/issues/226)) ([a93a52c](https://github.com/aphp/Cohort360-Back-end/commit/a93a52c99dd5e6b455e9e9f6ef7ffa6dbb267be1))



## [3.13.2](https://github.com/aphp/Cohort360-Back-end/compare/3.13.1...3.13.2) (2023-07-19)


### Bug Fixes

* **exports:** enable limit on cohorts list ([#219](https://github.com/aphp/Cohort360-Back-end/issues/219)) ([61f0990](https://github.com/aphp/Cohort360-Back-end/commit/61f09908f72ce2c93487522d9a83b7e9d2a0c0eb))



## [3.13.1](https://github.com/aphp/Cohort360-Back-end/compare/3.13.0...3.13.1) (2023-07-19)



# [3.13.0](https://github.com/aphp/Cohort360-Back-end/compare/3.12.5...3.13.0) (2023-07-07)


### Bug Fixes

* adjust email text for Hive export ([3972982](https://github.com/aphp/Cohort360-Back-end/commit/397298253c399eb98100e757a9fc8f9f022b22db))
* allow login via OIDc over maintenance phase ([4acf95b](https://github.com/aphp/Cohort360-Back-end/commit/4acf95b41bc041b73cd820c54e965b9049e55f9b))
* alter requests serializer to send RQSs data instead of UUIDs ([#199](https://github.com/aphp/Cohort360-Back-end/issues/199)) ([b295839](https://github.com/aphp/Cohort360-Back-end/commit/b295839ea51c11a18ef44faaa6d90e3075f101e9))
* **auth:** raise exception if user not found ([501a2b8](https://github.com/aphp/Cohort360-Back-end/commit/501a2b8ccabf78892b57f3680dda41834caec2e9))
* **confperimeters:** update compare cohort_id str ([#206](https://github.com/aphp/Cohort360-Back-end/issues/206)) ([7d7245e](https://github.com/aphp/Cohort360-Back-end/commit/7d7245ea3de15e15a508c7394d8437a39ebbaa65))
* fix Gunicorn log handler ([21de7e4](https://github.com/aphp/Cohort360-Back-end/commit/21de7e4a0075a3a6d2ea9096d4337c6cb75a619e))
* forward auth according to auth_method headers ([24b106b](https://github.com/aphp/Cohort360-Back-end/commit/24b106b1c3ea8c712ccfddb77edd4ef84ce603d8))
* login to Swagger ([b00cbcc](https://github.com/aphp/Cohort360-Back-end/commit/b00cbcce34a4ec109090f29d483d0a2cdb543fa3))
* logout user according to auth method headers ([0b828bd](https://github.com/aphp/Cohort360-Back-end/commit/0b828bd80e0e3aa3e151147b8f99319fa7e22a03))
* logout user according to auth method headers ([fe3cf3f](https://github.com/aphp/Cohort360-Back-end/commit/fe3cf3fd5ee424c73e5fe182ff071bfe56656a5b))
* manage request exception on refresh token ([b34e625](https://github.com/aphp/Cohort360-Back-end/commit/b34e625cba15ae135a532cc8402a2f15923efc7e))
* manage Swagger's initial request ([80b51a5](https://github.com/aphp/Cohort360-Back-end/commit/80b51a59b24071c1c9f51396c83e61dd74b47f8c))
* properly retrieve request payload on OIDC login ([001c1e9](https://github.com/aphp/Cohort360-Back-end/commit/001c1e944c6f9ec514454d512dedd1de60ac8b1f))
* retrieve accesses per perimeter ([#193](https://github.com/aphp/Cohort360-Back-end/issues/193)) ([dbe4be9](https://github.com/aphp/Cohort360-Back-end/commit/dbe4be91d707e763a73818564b13798a6122b177))
* send proper HTTP codes in accesses and perimeters responses ([18fa318](https://github.com/aphp/Cohort360-Back-end/commit/18fa318a23f34478b1c4b01859f56d5d02b2e30e))
* send proper response when user not found on OIDC login ([497eda2](https://github.com/aphp/Cohort360-Back-end/commit/497eda2e27f11eae572432594fe6b05eda32875a))
* update Nginx client_max_body_size param ([9ea1a42](https://github.com/aphp/Cohort360-Back-end/commit/9ea1a422eb0dbea05ce56623ce36edf519e91a68))
* verify jwt token signature ([ac50d18](https://github.com/aphp/Cohort360-Back-end/commit/ac50d18e9a5e9aea2b3f6ee58bafd8a43bfac439))


### Features

* add expiring accesses route ([#189](https://github.com/aphp/Cohort360-Back-end/issues/189)) ([9fe4ced](https://github.com/aphp/Cohort360-Back-end/commit/9fe4ced22e772dd4f686b313a36e990323a30f0a))
* add OIDC auth ([#191](https://github.com/aphp/Cohort360-Back-end/issues/191)) ([31db73c](https://github.com/aphp/Cohort360-Back-end/commit/31db73cd38479d4b706321a0bf0147b2b7f7b55a))
* add pagination to the `users within a role` view ([#200](https://github.com/aphp/Cohort360-Back-end/issues/200)) ([da33ac4](https://github.com/aphp/Cohort360-Back-end/commit/da33ac470a361bac932aa16156021b7bf668b23a))
* add patch function to upgrade serialized queries ([#207](https://github.com/aphp/Cohort360-Back-end/issues/207)) ([6ad7bef](https://github.com/aphp/Cohort360-Back-end/commit/6ad7bef682faca5444d37d3eea3b9c58ac982be6))
* add periodic task helper to ensure single run instead of one per django worker ([c261b62](https://github.com/aphp/Cohort360-Back-end/commit/c261b6243dba1bd0ff52b9830ea37f2a29a210e5))
* add version numbers to RQSs and fix old ones in DB ([#201](https://github.com/aphp/Cohort360-Back-end/issues/201)) ([c9f0b27](https://github.com/aphp/Cohort360-Back-end/commit/c9f0b278f87572c85f7e07557df83f04d1463999))
* **role:** add opposing patient role ([#186](https://github.com/aphp/Cohort360-Back-end/issues/186)) ([a4c6310](https://github.com/aphp/Cohort360-Back-end/commit/a4c6310e019c101446e5ff84331e8e27d75afebd))
* **role:** fix lint ([#188](https://github.com/aphp/Cohort360-Back-end/issues/188)) ([4aa6e70](https://github.com/aphp/Cohort360-Back-end/commit/4aa6e70df4c3c6aee48983d0d27571abc4b087b5))
* **roles:** add filtering and sorting to role users listing ([#203](https://github.com/aphp/Cohort360-Back-end/issues/203)) ([6ac52d1](https://github.com/aphp/Cohort360-Back-end/commit/6ac52d1adb411da55513fa6be3053a0860d93d78))


### Performance Improvements

* add Redis based cache ([#195](https://github.com/aphp/Cohort360-Back-end/issues/195)) ([5a97deb](https://github.com/aphp/Cohort360-Back-end/commit/5a97deb13ce2b8e44d0389d5cd0538f4a7158739))



## [3.12.4](https://github.com/aphp/Cohort360-Back-end/compare/3.12.3...3.12.4) (2023-05-12)


### Bug Fixes

* 3.12.4 squash migrations ([a68d503](https://github.com/aphp/Cohort360-Back-end/commit/a68d5035149083d098e042c8002b034353d0693c))
* adjust cohort and exports migrations ([9c9f986](https://github.com/aphp/Cohort360-Back-end/commit/9c9f9866d0d4e973a8134ab87856f96c180647bb))
* clean migrations ([c16aedf](https://github.com/aphp/Cohort360-Back-end/commit/c16aedfb5923231b67b184d87ef01906a1f0ad8f))
* force rm extra migration dir ([2b1dd37](https://github.com/aphp/Cohort360-Back-end/commit/2b1dd37fb7d91e84070fab8085ccf1f2b1343455))
* prepare squash script and isolate recent migrations ([#184](https://github.com/aphp/Cohort360-Back-end/issues/184)) ([67b48da](https://github.com/aphp/Cohort360-Back-end/commit/67b48daad0287dec83a56b95b1c0abe5b993668b))
* set default env vars values for tests ([87576c6](https://github.com/aphp/Cohort360-Back-end/commit/87576c64bb52d25a862488a81e9d18018d3c7ab6))
* squash migrations on starting container ([9f61182](https://github.com/aphp/Cohort360-Back-end/commit/9f61182f4fe6ddb35c674df174354cdfb53a38d2))


### Features

* alert users on accesses expiry ([#183](https://github.com/aphp/Cohort360-Back-end/issues/183)) ([c983a7c](https://github.com/aphp/Cohort360-Back-end/commit/c983a7c796620ac24def1d7ab60f3670737980f8))



## [3.12.3](https://github.com/aphp/Cohort360-Back-end/compare/3.11.9-b...3.12.3) (2023-05-05)


### Bug Fixes

* up to v3.12.3 after hotfix prod ([ac1056e](https://github.com/aphp/Cohort360-Back-end/commit/ac1056e22d49b8ce40c9f7320b50990775f77142))



## [3.11.9-b](https://github.com/aphp/Cohort360-Back-end/compare/3.11.9-a...3.11.9-b) (2023-05-05)


### Bug Fixes

* add inferior_levels and above_levels to perimeters serializers ([ca12460](https://github.com/aphp/Cohort360-Back-end/commit/ca124605d28e80839273bf014caee694ff80cee8))
* add provider_id on profile creation ([9e4dd91](https://github.com/aphp/Cohort360-Back-end/commit/9e4dd91ed874c5916b0a32d226af4ba8549b6431))
* do not create simple user on login ([4c10bf0](https://github.com/aphp/Cohort360-Back-end/commit/4c10bf091b608a21f1cfc35d2d8336c13aed757e))
* fix linter ([e34b2ba](https://github.com/aphp/Cohort360-Back-end/commit/e34b2bae0967ad170aa45fff457053bc5b0ec1da))
* return a JsonResponse in case of a JWT server error ([1a77001](https://github.com/aphp/Cohort360-Back-end/commit/1a7700139ee50aae9ac23a46c2cedc7e580e5795))
* test create dated measures and cancel running jobs ([ad5ea56](https://github.com/aphp/Cohort360-Back-end/commit/ad5ea56e1e4a144830d9b4b167db7774341fe1df))
* up to v3.11.9-b ([a8cdcf1](https://github.com/aphp/Cohort360-Back-end/commit/a8cdcf12015dbcb456a74886126cef365c73f923))


### Features

* **auth:** return a proper 401 http error on invalid login ([#179](https://github.com/aphp/Cohort360-Back-end/issues/179)) ([565126d](https://github.com/aphp/Cohort360-Back-end/commit/565126d205c562178addba556c9c0b075b22f7ad))



## [3.11.9-a](https://github.com/aphp/Cohort360-Back-end/compare/3.12.2...3.11.9-a) (2023-04-28)


### Bug Fixes

* add migration to patch perimeters_ids on RQSs ([1c1e14e](https://github.com/aphp/Cohort360-Back-end/commit/1c1e14eb15b5de4cdd9f2a8278e29dc3cb6d1c34))
* adjust migration dependency ([07c1108](https://github.com/aphp/Cohort360-Back-end/commit/07c1108f81390d54e8ef036f4a094433d77b4d53))
* clear cache on patch cohorts ([e8e3337](https://github.com/aphp/Cohort360-Back-end/commit/e8e3337ad4cc1ee605bc32634af4a7eff7558cc0))
* disable buggy cache ([ace7a34](https://github.com/aphp/Cohort360-Back-end/commit/ace7a34d327ccae0fe5fe876045ba61580c1b103))
* fhir OIDC auth to back ([86ad8f9](https://github.com/aphp/Cohort360-Back-end/commit/86ad8f98520f5b7662e545d9e38eed67a3c5c28d))
* Fhir OIDC auth to back ([f895234](https://github.com/aphp/Cohort360-Back-end/commit/f8952345e547ce09d0fb6b36a47fccedea792c61))
* fix flake8 errors ([f92f93f](https://github.com/aphp/Cohort360-Back-end/commit/f92f93fdcbac2fbd455d3180a5dd86bdaf8dd65e))
* flake8 error ([b3cbcb1](https://github.com/aphp/Cohort360-Back-end/commit/b3cbcb14053ae39f6b7e4196e7a6d2a2d1411d8b))
* improve response time ([#153](https://github.com/aphp/Cohort360-Back-end/issues/153)) ([c7c962f](https://github.com/aphp/Cohort360-Back-end/commit/c7c962f678a31a398c1653194a9c41e352561acc))
* log job response from CRB ([08fc046](https://github.com/aphp/Cohort360-Back-end/commit/08fc046fee5f187daf70d473aa67fb667edcbd14))
* notify creator not owner when export is done ([e137450](https://github.com/aphp/Cohort360-Back-end/commit/e1374507a6a5228f057176e05a25e98281f77f17))
* **perimeters:** add type and parent_id filter multi value refs:dev/c… ([#147](https://github.com/aphp/Cohort360-Back-end/issues/147)) ([dfb9e0c](https://github.com/aphp/Cohort360-Back-end/commit/dfb9e0ca411664248416ce9b6934b64d28a6c890))
* **perimeters:** change mapping, add above_list_ids ([#166](https://github.com/aphp/Cohort360-Back-end/issues/166)) ([471edc4](https://github.com/aphp/Cohort360-Back-end/commit/471edc44bff1c5518fdbb411265049f83d0f32cf))
* **perimeters:** change type mapping refs:dev/cohort360/gestion-de-pr… ([#150](https://github.com/aphp/Cohort360-Back-end/issues/150)) ([2e6481f](https://github.com/aphp/Cohort360-Back-end/commit/2e6481fe280df88efea38ed132b699d681de1360))
* rearrange cohort migrations files ([61997b6](https://github.com/aphp/Cohort360-Back-end/commit/61997b657957d1d4304a695ce663424c300a9fc1))
* remove cache for resources in cohort app ([78c6177](https://github.com/aphp/Cohort360-Back-end/commit/78c61774ee85394db55ed5a7b73ee500974b28e7))
* remove Django's parallel testing as not supported by gitlab runners ([c1122e5](https://github.com/aphp/Cohort360-Back-end/commit/c1122e5538302733a7e3d3d0d08e3778b19b8bf3))
* remove lof file rotation ([2fe52f3](https://github.com/aphp/Cohort360-Back-end/commit/2fe52f318b55730f5728a1c4b4198a7dbffdb271))
* remove unused import ([269792c](https://github.com/aphp/Cohort360-Back-end/commit/269792c39c8c519aa51062344dd2a1d994d9b6de))
* return proper response on export error ([f4f4b89](https://github.com/aphp/Cohort360-Back-end/commit/f4f4b89a189d44d0d7fb135efc645901319e041f))
* revert search users by provider_source_value ([ae403bf](https://github.com/aphp/Cohort360-Back-end/commit/ae403bfca2b1ab5d90c84d0e7bedb88048c82000))
* run parallel tests Django way ([b51aa62](https://github.com/aphp/Cohort360-Back-end/commit/b51aa62e977e7fe8d87d3063cb6b24919a694d27))
* search fields on exports list ([d2606f5](https://github.com/aphp/Cohort360-Back-end/commit/d2606f5f28cf857beccb0535eae5aee505ce5d61))
* temporarily remove cache for single DatedMeasure and RQS retrieve ([7899323](https://github.com/aphp/Cohort360-Back-end/commit/7899323089c0c03dc613dfed7a9668cd22056ac0))
* temporarily remove cache for single DatedMeasure retrieve ([12ac462](https://github.com/aphp/Cohort360-Back-end/commit/12ac462c251472ecf218d2b21d454912f64f841e))
* temporarily remove cache for single DatedMeasure retrieve ([4e48817](https://github.com/aphp/Cohort360-Back-end/commit/4e4881766599a470be56ae19bb7d45b335809bcc))
* update influxdb token env var ([588924e](https://github.com/aphp/Cohort360-Back-end/commit/588924ead464621e88c89711cb68036282a8b96e))
* update page_size to 20 in tests ([685e793](https://github.com/aphp/Cohort360-Back-end/commit/685e7930b5969898d493389b03188f0a14de16ff))


### Features

* make infra api calls async ([#167](https://github.com/aphp/Cohort360-Back-end/issues/167)) ([ee27843](https://github.com/aphp/Cohort360-Back-end/commit/ee278436f5e3446077baf6a228049afad8873e66))
* run parallel tests gitlab ci ([#143](https://github.com/aphp/Cohort360-Back-end/issues/143)) ([b518a32](https://github.com/aphp/Cohort360-Back-end/commit/b518a325415e1e5c191d837fe41854b5ee872cc7))


### Performance Improvements

* add cache to improve response time ([#160](https://github.com/aphp/Cohort360-Back-end/issues/160)) ([2b38d25](https://github.com/aphp/Cohort360-Back-end/commit/2b38d257d59383cf34bbe8cfc5a2b952a154bb77))
* add InfluxDB middleware to collect metrics ([#148](https://github.com/aphp/Cohort360-Back-end/issues/148)) ([6c8a782](https://github.com/aphp/Cohort360-Back-end/commit/6c8a7823c39272c2e0ab91b2ca3314e288785bcf))
* cache exports requests and fix tests ([#154](https://github.com/aphp/Cohort360-Back-end/issues/154)) ([01f0c5b](https://github.com/aphp/Cohort360-Back-end/commit/01f0c5be037e055f6a9a9678ff1cf336f9d3cfc8))
* improve response time ([#162](https://github.com/aphp/Cohort360-Back-end/issues/162)) ([88fd9dd](https://github.com/aphp/Cohort360-Back-end/commit/88fd9dd314b223260d82245241d23a02035dea10))



## [3.12.5](https://github.com/aphp/Cohort360-Back-end/compare/3.12.4...3.12.5) (2023-06-07)


### Bug Fixes

* 3.12.5 increase Nginx client_max_body_size param ([#194](https://github.com/aphp/Cohort360-Back-end/issues/194)) ([23c300b](https://github.com/aphp/Cohort360-Back-end/commit/23c300b5f3483fa955291fb198f40b2855f721e2))
* up to v3.12.3 after hotfix prod ([b210e77](https://github.com/aphp/Cohort360-Back-end/commit/b210e7790213a6db430ac6e1f81193e244117098))



## [3.12.4](https://github.com/aphp/Cohort360-Back-end/compare/3.12.3...3.12.4) (2023-05-12)


### Bug Fixes

* 3.12.4 squash migrations ([a68d503](https://github.com/aphp/Cohort360-Back-end/commit/a68d5035149083d098e042c8002b034353d0693c))
* adjust cohort and exports migrations ([9c9f986](https://github.com/aphp/Cohort360-Back-end/commit/9c9f9866d0d4e973a8134ab87856f96c180647bb))
* squash migrations on starting container ([9f61182](https://github.com/aphp/Cohort360-Back-end/commit/9f61182f4fe6ddb35c674df174354cdfb53a38d2))



## [3.12.3](https://github.com/aphp/Cohort360-Back-end/compare/3.11.9-b...3.12.3) (2023-05-05)


### Bug Fixes

* up to v3.12.3 after hotfix prod ([ac1056e](https://github.com/aphp/Cohort360-Back-end/commit/ac1056e22d49b8ce40c9f7320b50990775f77142))



## [3.12.2](https://github.com/aphp/Cohort360-Back-end/compare/3.12.1...3.12.2) (2023-04-28)


### Bug Fixes

* notify creator not owner when export is done ([#176](https://github.com/aphp/Cohort360-Back-end/issues/176)) ([5ea8f31](https://github.com/aphp/Cohort360-Back-end/commit/5ea8f312ecebb3c0ccdc8da0511a78c5aec04136))
* notify creator not owner when export is done ([#177](https://github.com/aphp/Cohort360-Back-end/issues/177)) ([e4140e1](https://github.com/aphp/Cohort360-Back-end/commit/e4140e1147a865d60435908e3ed423c091973208))
* remove unused import ([e51b6e7](https://github.com/aphp/Cohort360-Back-end/commit/e51b6e714c045267b47882554bb652931abc8a96))



## [3.12.1](https://github.com/aphp/Cohort360-Back-end/compare/3.12.0...3.12.1) (2023-04-26)


### Bug Fixes

* disable buggy cache ([6a0116b](https://github.com/aphp/Cohort360-Back-end/commit/6a0116bce9fd749c990d57f958152a5da86a7bce))
* remove buggy cache ([#174](https://github.com/aphp/Cohort360-Back-end/issues/174)) ([193e21b](https://github.com/aphp/Cohort360-Back-end/commit/193e21b4b8d0d5a983be8938622db7e5bb6546b7))



# [3.12.0](https://github.com/aphp/Cohort360-Back-end/compare/3.11.9...3.12.0) (2023-04-03)


### Bug Fixes

* flake8 error ([2333009](https://github.com/aphp/Cohort360-Back-end/commit/23330096adee2e52ff69f057c2ff6328f2499eea))
* remove cache for resources in cohort app ([#163](https://github.com/aphp/Cohort360-Back-end/issues/163)) ([d9ce471](https://github.com/aphp/Cohort360-Back-end/commit/d9ce471a1c1a5ef846f6d90a1eb6f59611c4272f))



## [3.11.9-b](https://github.com/aphp/Cohort360-Back-end/compare/3.11.9-a...3.11.9-b) (2023-05-05)


### Bug Fixes

* add provider_id on profile creation ([9e4dd91](https://github.com/aphp/Cohort360-Back-end/commit/9e4dd91ed874c5916b0a32d226af4ba8549b6431))
* do not create simple user on login ([4c10bf0](https://github.com/aphp/Cohort360-Back-end/commit/4c10bf091b608a21f1cfc35d2d8336c13aed757e))
* up to v3.11.9-b ([a8cdcf1](https://github.com/aphp/Cohort360-Back-end/commit/a8cdcf12015dbcb456a74886126cef365c73f923))



## [3.11.9-a](https://github.com/aphp/Cohort360-Back-end/compare/3.12.2...3.11.9-a) (2023-04-28)


### Bug Fixes

* notify creator not owner when export is done ([e137450](https://github.com/aphp/Cohort360-Back-end/commit/e1374507a6a5228f057176e05a25e98281f77f17))



## [3.12.2](https://github.com/aphp/Cohort360-Back-end/compare/3.12.1...3.12.2) (2023-04-28)


### Bug Fixes

* notify creator not owner when export is done ([#176](https://github.com/aphp/Cohort360-Back-end/issues/176)) ([5ea8f31](https://github.com/aphp/Cohort360-Back-end/commit/5ea8f312ecebb3c0ccdc8da0511a78c5aec04136))
* notify creator not owner when export is done ([#177](https://github.com/aphp/Cohort360-Back-end/issues/177)) ([e4140e1](https://github.com/aphp/Cohort360-Back-end/commit/e4140e1147a865d60435908e3ed423c091973208))
* remove unused import ([e51b6e7](https://github.com/aphp/Cohort360-Back-end/commit/e51b6e714c045267b47882554bb652931abc8a96))



## [3.12.1](https://github.com/aphp/Cohort360-Back-end/compare/3.12.0...3.12.1) (2023-04-26)


### Bug Fixes

* disable buggy cache ([6a0116b](https://github.com/aphp/Cohort360-Back-end/commit/6a0116bce9fd749c990d57f958152a5da86a7bce))
* remove buggy cache ([#174](https://github.com/aphp/Cohort360-Back-end/issues/174)) ([193e21b](https://github.com/aphp/Cohort360-Back-end/commit/193e21b4b8d0d5a983be8938622db7e5bb6546b7))



# [3.12.0](https://github.com/aphp/Cohort360-Back-end/compare/3.11.9...3.12.0) (2023-04-03)


### Bug Fixes

* flake8 error ([2333009](https://github.com/aphp/Cohort360-Back-end/commit/23330096adee2e52ff69f057c2ff6328f2499eea))
* remove cache for resources in cohort app ([#163](https://github.com/aphp/Cohort360-Back-end/issues/163)) ([d9ce471](https://github.com/aphp/Cohort360-Back-end/commit/d9ce471a1c1a5ef846f6d90a1eb6f59611c4272f))



## [3.11.9](https://github.com/aphp/Cohort360-Back-end/compare/3.11.8...3.11.9) (2023-03-31)



## [3.11.8](https://github.com/aphp/Cohort360-Back-end/compare/3.11.7...3.11.8) (2023-03-31)


### Bug Fixes

* fhir OIDC auth to back ([#157](https://github.com/aphp/Cohort360-Back-end/issues/157)) ([2d7c5d2](https://github.com/aphp/Cohort360-Back-end/commit/2d7c5d26ad7582da2c75aa6551d64b6c6fe891b5))



## [3.11.7](https://github.com/aphp/Cohort360-Back-end/compare/3.11.6...3.11.7) (2023-03-27)


### Bug Fixes

* return proper response on export error ([#155](https://github.com/aphp/Cohort360-Back-end/issues/155)) ([5386562](https://github.com/aphp/Cohort360-Back-end/commit/538656252875971ff6af20c060ae4197d40869be))



## [3.11.6](https://github.com/aphp/Cohort360-Back-end/compare/3.11.5...3.11.6) (2023-03-17)


### Bug Fixes

* hotfix v3.11.6 for cohort migrations order ([#152](https://github.com/aphp/Cohort360-Back-end/issues/152)) ([8ac561f](https://github.com/aphp/Cohort360-Back-end/commit/8ac561ffdb1b4e35ae5de78d3a397c78b9518a08))



## [3.11.5](https://github.com/aphp/Cohort360-Back-end/compare/3.11.4...3.11.5) (2023-03-15)


### Bug Fixes

* **perimeters:** add type and parent_id filter multi value refs:dev/c… ([#149](https://github.com/aphp/Cohort360-Back-end/issues/149)) ([8b2a849](https://github.com/aphp/Cohort360-Back-end/commit/8b2a8490538eb861c5494c814e40bf5521870e45))



## [3.11.4](https://github.com/aphp/Cohort360-Back-end/compare/3.11.3...3.11.4) (2023-03-14)


### Bug Fixes

* hotfix v3.11.4 ([85ad05e](https://github.com/aphp/Cohort360-Back-end/commit/85ad05e806c836f8bb7e3667d397015fd3f3d3b3))
* remove log file rotation ([#146](https://github.com/aphp/Cohort360-Back-end/issues/146)) ([1b3e6af](https://github.com/aphp/Cohort360-Back-end/commit/1b3e6af2e854c761f3bcbafe470f59e85d9aeff7))



## [3.11.3](https://github.com/aphp/Cohort360-Back-end/compare/3.11.2...3.11.3) (2023-03-06)



## [3.11.1](https://github.com/aphp/Cohort360-Back-end/compare/3.11.0...3.11.1) (2023-03-01)



## [3.10.3](https://github.com/aphp/Cohort360-Back-end/compare/3.10.2...3.10.3) (2023-02-09)



## [3.9.3](https://github.com/aphp/Cohort360-Back-end/compare/3.9.2...3.9.3) (2023-01-10)



# [3.9.0](https://github.com/aphp/Cohort360-Back-end/compare/3.8.5...3.9.0) (2023-01-05)



## [3.8.5](https://github.com/aphp/Cohort360-Back-end/compare/3.8.4...3.8.5) (2022-12-21)



## [3.8.4](https://github.com/aphp/Cohort360-Back-end/compare/3.8.3...3.8.4) (2022-12-21)


### Reverts

* Revert "Launch celery in detach mode" ([331b0f6](https://github.com/aphp/Cohort360-Back-end/commit/331b0f6fd5982d87566ee3dd332d9228c12e88ab))



## [3.8.3](https://github.com/aphp/Cohort360-Back-end/compare/3.8.2...3.8.3) (2022-12-15)



## [3.8.2](https://github.com/aphp/Cohort360-Back-end/compare/3.8.1...3.8.2) (2022-12-08)



# [3.8.0](https://github.com/aphp/Cohort360-Back-end/compare/3.7.5...3.8.0) (2022-12-05)



## [3.7.5](https://github.com/aphp/Cohort360-Back-end/compare/3.7.4...3.7.5) (2022-12-02)



## [3.7.4](https://github.com/aphp/Cohort360-Back-end/compare/3.7.3...3.7.4) (2022-11-29)


### Reverts

* Revert "HOT FIX name perimeter table in migration table" ([f1d83b8](https://github.com/aphp/Cohort360-Back-end/commit/f1d83b85e12e85ceae48577557b8375d3910096e))



## [3.7.3](https://github.com/aphp/Cohort360-Back-end/compare/3.7.2...3.7.3) (2022-11-24)



## [3.7.2](https://github.com/aphp/Cohort360-Back-end/compare/3.7.1...3.7.2) (2022-11-23)


### Bug Fixes

* email formatting ([83e7b88](https://github.com/aphp/Cohort360-Back-end/commit/83e7b889fcb9a3f3918d816d8825630b0557f4fc))
* read env variables directly from os.environ instead of loading a non-existing .env file in accesses app. ([e831f21](https://github.com/aphp/Cohort360-Back-end/commit/e831f2133f5b8816ee19679544205c7566f4dbd6))


### Reverts

* Revert "Rollback filters in /cohorts" ([c734e78](https://github.com/aphp/Cohort360-Back-end/commit/c734e78fdd05ee9e6ca6936c54479539633ca73a))
* Revert "Rollback filters in /cohorts" ([532c3d9](https://github.com/aphp/Cohort360-Back-end/commit/532c3d9afb94b479597d8e7f19ded0e4de8aaf5b))
* Revert "Rollback filters in /cohorts" ([abe993d](https://github.com/aphp/Cohort360-Back-end/commit/abe993d17cd7dc99ab25b8d10bb2c34abd874d61))
* Revert "[3.7.0-SNAPSHOT] removed CodeQL analysis as it's no longer available for private repo" ([1818329](https://github.com/aphp/Cohort360-Back-end/commit/1818329be01a34688b22c663ac7484cc4c34f7eb))



## [3.6.5](https://github.com/aphp/Cohort360-Back-end/compare/3.6.4...3.6.5) (2022-09-05)



## [3.6.4](https://github.com/aphp/Cohort360-Back-end/compare/3.6.3...3.6.4) (2022-08-29)



## [3.6.3](https://github.com/aphp/Cohort360-Back-end/compare/3.6.2...3.6.3) (2022-08-23)



## [3.6.2](https://github.com/aphp/Cohort360-Back-end/compare/3.6.1...3.6.2) (2022-08-23)



## [3.6.1](https://github.com/aphp/Cohort360-Back-end/compare/3.6.0...3.6.1) (2022-08-22)



# [3.6.0](https://github.com/aphp/Cohort360-Back-end/compare/3.5.3...3.6.0) (2022-08-22)



## [3.5.3](https://github.com/aphp/Cohort360-Back-end/compare/3.5.2...3.5.3) (2022-08-10)



## [3.5.2](https://github.com/aphp/Cohort360-Back-end/compare/3.5.1...3.5.2) (2022-08-08)



## [3.5.1](https://github.com/aphp/Cohort360-Back-end/compare/3.5.0...3.5.1) (2022-08-08)



# 3.5.0 (2022-08-02)



