import requests
import jwt
from datetime import datetime, timedelta
import time
import json
from enum import Enum

from .resources import *

ALGORITHM = 'ES256'
BASE_API = "https://api.appstoreconnect.apple.com"


class HttpMethod(Enum):
	GET = 1
	POST = 2
	PATCH = 3


class Api:

	def __init__(self, key_id, key_file, issuer_id):
		self._token = None
		self.token_gen_date = None
		self.exp = None
		self.key_id = key_id
		self.key_file = key_file
		self.issuer_id = issuer_id
		self._debug = False
		token = self.token  # generate first token

	def _generate_token(self):
		key = open(self.key_file, 'r').read()
		self.token_gen_date = datetime.now()
		exp = int(time.mktime((self.token_gen_date + timedelta(minutes=20)).timetuple()))
		return jwt.encode({'iss': self.issuer_id, 'exp': exp, 'aud': 'appstoreconnect-v1'}, key,
		                   headers={'kid': self.key_id, 'typ': 'JWT'}, algorithm=ALGORITHM).decode('ascii')

	def _get_resource(self, Resource, resource_id):
		url = "%s%s/%s" % (BASE_API, Resource.endpoint, resource_id)
		payload = self._api_call(url)
		return Resource(payload.get('data', {}))

	def _get_resources(self, Resource):
		url = "%s%s" % (BASE_API, Resource.endpoint)

		while url:
			payload = self._api_call(url)

			for data in payload.get('data', []):
				resource = Resource(data)
				yield resource
			url = payload.get('links', {}).get('next', None)

	def _api_call(self, url, method=HttpMethod.GET, post_data=None):
		headers = {"Authorization": "Bearer %s" % self.token}
		if self._debug:
			print(url)
		r = {}

		if method == HttpMethod.GET:
			r = requests.get(url, headers=headers)
		elif method == HttpMethod.POST:
			headers["Content-Type"] = "application/json"
			r = requests.post(url=url, headers=headers, data=json.dumps(post_data))
		elif method == HttpMethod.PATCH:
			headers["Content-Type"] = "application/json"
			r = requests.patch(url=url, headers=headers, data=json.dumps(post_data))

		content_type = r.headers['content-type']

		if content_type == "application/json":
			return r.json()
		else:
			if not 200 <= r.status_code <= 299:
				print("Error [%d][%s]" % (r.status_code, r.content))

	@property
	def token(self):
		# generate a new token every 15 minutes
		if not self._token or self.token_gen_date + timedelta(minutes=15) > datetime.now():
			self._token = self._generate_token()

		return self._token

	# Users and Roles
	def list_users(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_users
		:return: an iterator over User resources
		"""
		return self._get_resources(User)

	def list_invited_users(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_invited_users
		:return: an iterator over UserInvitation resources
		"""
		return self._get_resources(UserInvitation)

	# Beta Testers and Groups
	def list_beta_testers(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_beta_testers
		:return: an iterator over BetaTester resources
		"""
		return self._get_resources(BetaTester)

	def list_beta_groups(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_beta_groups
		:return: an iterator over BetaGroup resources
		"""
		return self._get_resources(BetaGroup)

	# TODO: implement these function using Resource
	def create_beta_tester(self, beta_group_id, email, first_name, last_name):
		post_data = {'data': {'attributes': {'email': email, 'firstName': first_name, 'lastName': last_name}, 'relationships': {'betaGroups': {'data': [{ 'id': beta_group_id ,'type': 'betaGroups'}]}}, 'type': 'betaTesters'}}
		return self._api_call("/v1/betaTesters", HttpMethod.POST, post_data)

	def create_beta_group(self, group_name, app_id):
		post_data = {'data': {'attributes': {'name': group_name}, 'relationships': {'app': {'data': {'id': app_id, 'type': 'apps'}}}, 'type': 'betaGroups'}}
		return self._api_call(BASE_API + "/v1/betaGroups", HttpMethod.POST, post_data)

	def add_build_to_beta_group(self, beta_group_id, build_id):
		post_data = {'data': [{ 'id': build_id, 'type': 'builds'}]}
		return self._api_call(BASE_API + "/v1/betaGroups/" + beta_group_id + "/relationships/builds", HttpMethod.POST, post_data)

	# App Resources
	def read_app_information(self, app_ip):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/read_app_information
		:param app_ip:
		:return: an App resource
		"""
		return self._get_resource(App, app_ip)

	def list_apps(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_apps
		:return: an iterator over App resources
		"""
		return self._get_resources(App)

	# TODO: handle filters on get_resources()
	def app_for_sku(self, sku):
		return self._api_call(BASE_API + "/v1/apps?filter[sku]=" + sku)

	def list_prerelease_versions(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_prerelease_versions
		:return: an iterator over PreReleaseVersions resources
		"""
		return self._get_resources(PreReleaseVersions)

	def list_beta_app_localizations(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_beta_app_localizations
		:return: an iterator over BetaAppLocalizations resources
		"""
		return self._get_resources(BetaAppLocalizations)

	def list_app_encryption_declarations(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_app_encryption_declarations
		:return: an iterator over AppEncryptionDeclaration resources
		"""
		return self._get_resources(AppEncryptionDeclaration)

	def list_beta_license_agreements(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_beta_license_agreements
		:return: an iterator over BetaLicenseAgreement resources
		"""
		return self._get_resources(BetaLicenseAgreement)

	# Build Resources
	def list_builds(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_builds
		:return: an iterator over Build resources
		"""
		return self._get_resources(Build)

	# TODO: handle filters on get_resources()
	def builds_for_app(self, app_id):
		return self._api_call(BASE_API + "/v1/builds?filter[app]=" + app_id)

	def build_processing_state(self, app_id, version):
		return self._api_call(BASE_API + "/v1/builds?filter[app]=" + app_id + "&filter[version]=" + version + "&fields[builds]=processingState")

	# TODO: implement this function using Resource
	def set_uses_non_encryption_exemption_setting(self, build_id, uses_non_encryption_exemption_setting):
		post_data = {'data': {'attributes': {'usesNonExemptEncryption': uses_non_encryption_exemption_setting}, 'id': build_id, 'type': 'builds'}}
		return self._api_call(BASE_API + "/v1/builds/" + build_id, HttpMethod.PATCH, post_data)

	def list_build_beta_details(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_build_beta_details
		:return: an iterator over BuildBetaDetails resources
		"""
		return self._get_resources(BuildBetaDetails)

	# TODO: handle filters on get_resources()
	def beta_build_localizations_for_build(self, build_id):
		return self._api_call(BASE_API + "/v1/betaBuildLocalizations?filter[build]=" + build_id)

	def beta_build_localizations_for_build_and_locale(self, build_id, locale):
		return self._api_call(BASE_API +  "/v1/betaBuildLocalizations?filter[build]=" + build_id + "&filter[locale]=" + locale)

	def create_beta_build_localization(self, build_id, locale, whatsNew):
		post_data = {'data': { 'type': 'betaBuildLocalizations', 'relationships': {'build': {'data': {'id': build_id, 'type': 'builds'}}}, 'attributes': { 'locale': locale, 'whatsNew': whatsNew}}}
		return self._api_call(BASE_API +  "/v1/betaBuildLocalizations", HttpMethod.POST, post_data)

	def modify_beta_build_localization(self, beta_build_localization_id, whatsNew):
		post_data = {'data': { 'type': 'betaBuildLocalizations', 'id': beta_build_localization_id, 'attributes': {'whatsNew': whatsNew}}}
		return self._api_call(BASE_API +  "/v1/betaBuildLocalizations/" + beta_build_localization_id, HttpMethod.PATCH, post_data)

	def list_beta_build_localizations(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_beta_build_localizations
		:return: an iterator over BetaBuildLocalization resources
		"""
		return self._get_resources(BetaBuildLocalization)

	def list_beta_app_review_details(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_beta_app_review_details
		:return: an iterator over BetaAppReviewDetail resources
		"""
		return self._get_resources(BetaAppReviewDetail)

	def list_beta_app_review_submissions(self):
		"""
		:reference: https://developer.apple.com/documentation/appstoreconnectapi/list_beta_app_review_submissions
		:return: an iterator over BetaAppReviewSubmission resources
		"""
		return self._get_resources(BetaAppReviewSubmission)

	# TODO: implement these function using Resource
	def submit_app_for_beta_review(self, build_id):
		post_data = {'data': { 'type': 'betaAppReviewSubmissions', 'relationships': {'build': {'data': {'id': build_id, 'type': 'builds'}}}}}
		return self._api_call(BASE_API + "/v1/betaAppReviewSubmissions", HttpMethod.POST, post_data)

	# finance reports
	def finance_reports(self):
		return self._get_resources(FinanceReport)