# -*- coding: utf-8 -*-
from urlparse import urlparse

from django.contrib.auth import get_user_model
from django.shortcuts import resolve_url
from django.test import TestCase


class SetupTest(TestCase):
    def test_initial_setup_redirect(self):
        resp = self.client.get(resolve_url('login'))

        self.assertEqual(resp.status_code, 302)

        url = urlparse(resp['Location'])
        self.assertEqual(url.path, resolve_url('first_time_setup'))

        # Don't redirect if there's already a user
        get_user_model().objects.create_user(username='test')
        resp = self.client.get(resolve_url('login'))
        self.assertEqual(resp.status_code, 200)

    def test_initial_setup_requires(self):
        resp = self.client.post(resolve_url('first_time_setup'))
        self.assertEqual(resp.status_code, 400)

    def test_initial_setup_post(self):
        resp = self.client.post(
            resolve_url('first_time_setup'),
            data={
                'username': '',
                'password': 'pass'
            })
        self.assertEqual(resp.status_code, 400)

        resp = self.client.post(
            resolve_url('first_time_setup'),
            data={
                'username': 'test',
                'password': ''
            })
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(get_user_model().objects.exists())

        resp = self.client.post(
            resolve_url('first_time_setup'),
            data={
                'username': 'test',
                'password': 'pass'
            })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(get_user_model().objects.exists())

    def test_initial_setup_post_with_email(self):
        resp = self.client.post(
            resolve_url('first_time_setup'),
            data={
                'username': 'test',
                'email': 'fail',
                'password': 'pass'
            })
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(get_user_model().objects.exists())

        resp = self.client.post(
            resolve_url('first_time_setup'),
            data={
                'username': 'test',
                'email': 'real@email.com',
                'password': 'pass'
            })
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(get_user_model().objects.exists())

    def test_cant_setup_with_existing_user(self):
        get_user_model().objects.create_user(username='test')

        resp = self.client.post(
            resolve_url('first_time_setup'),
            data={
                'username': 'test',
                'email': 'real@email.com',
                'password': 'pass'
            })
        self.assertEqual(get_user_model().objects.count(), 1)

