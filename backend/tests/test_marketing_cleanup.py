import os
import sys
import unittest
from unittest.mock import AsyncMock, patch

os.environ.setdefault('APP_ENVIRONMENT', 'development')

REPO_BACKEND = '/home/runner/work/Amarktai-Marketing/Amarktai-Marketing/backend'
if REPO_BACKEND not in sys.path:
    sys.path.insert(0, REPO_BACKEND)

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.db.base import Base, get_db
from app.main import app


TEST_ENGINE = create_engine(
    'sqlite://',
    connect_args={'check_same_thread': False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


class MarketingCleanupEndpointTests(unittest.TestCase):
    password = 'ComplexPass123!'

    def setUp(self) -> None:
        Base.metadata.drop_all(bind=TEST_ENGINE)
        Base.metadata.create_all(bind=TEST_ENGINE)

    def register_and_login(self, email: str) -> dict:
        client.post('/api/v1/auth/register', json={'email': email, 'password': self.password, 'name': 'Test User'})
        response = client.post('/api/v1/auth/login', json={'email': email, 'password': self.password})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        return {'Authorization': f"Bearer {data['access_token']}"}

    def create_business(self, headers: dict[str, str]) -> str:
        response = client.post(
            '/api/v1/webapps/',
            headers=headers,
            json={
                'name': 'Blue Ridge Equestrian Centre',
                'url': 'https://example.com',
                'description': 'Horse riding lessons and equine experiences.',
                'category': 'equine',
                'target_audience': 'horse owners',
                'key_features': ['trail rides', 'dressage coaching'],
                'market_location': 'Virginia',
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()['id']

    def list_content(self, headers: dict[str, str], webapp_id: str) -> list[dict]:
        response = client.get(f'/api/v1/content/webapp/{webapp_id}', headers=headers)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_owner_login_has_unrestricted_access(self):
        headers = self.register_and_login('amarktainetwork@gmail.com')
        me = client.get('/api/v1/users/me', headers=headers)
        self.assertEqual(me.status_code, 200, me.text)
        payload = me.json()
        self.assertTrue(payload['is_admin'])
        self.assertEqual(payload['effective_plan'], 'enterprise')
        billing = client.get('/api/v1/settings/billing', headers=headers)
        self.assertEqual(billing.status_code, 200, billing.text)
        billing_payload = billing.json()
        self.assertFalse(billing_payload['billing_enabled'])
        self.assertTrue(billing_payload['unlimited_content_quota'])

    def test_preview_is_ephemeral_and_save_creates_one_draft(self):
        headers = self.register_and_login('preview@example.com')
        webapp_id = self.create_business(headers)
        before = self.list_content(headers, webapp_id)
        preview = client.post(
            '/api/v1/content/preview',
            headers=headers,
            json={'webapp_id': webapp_id, 'platform': 'instagram', 'format': 'text_post', 'objective': 'awareness'},
        )
        self.assertEqual(preview.status_code, 200, preview.text)
        after_preview = self.list_content(headers, webapp_id)
        self.assertEqual(len(before), len(after_preview))
        preview_payload = preview.json()
        self.assertIn('preview_id', preview_payload)
        saved = client.post('/api/v1/content/preview/save', headers=headers, json={'preview_id': preview_payload['preview_id']})
        self.assertEqual(saved.status_code, 200, saved.text)
        after_save = self.list_content(headers, webapp_id)
        self.assertEqual(len(after_save), len(before) + 1)

    def test_ad_campaign_preview_returns_structured_output(self):
        headers = self.register_and_login('campaign@example.com')
        webapp_id = self.create_business(headers)
        response = client.post(
            '/api/v1/content/preview',
            headers=headers,
            json={'webapp_id': webapp_id, 'platform': 'facebook', 'format': 'ad_campaign', 'objective': 'leads', 'offer': 'Free trial lesson'},
        )
        self.assertEqual(response.status_code, 200, response.text)
        preview = response.json()['preview']
        structured = preview['structured_output']
        self.assertEqual(preview['format'], 'ad_campaign')
        for key in ['campaign_concept', 'hooks', 'headline', 'primary_text', 'cta', 'creative_brief', 'placements', 'asset_recommendation', 'schedule_suggestion']:
            self.assertIn(key, structured)

    def test_short_video_and_media_outputs_are_truthful(self):
        headers = self.register_and_login('video@example.com')
        webapp_id = self.create_business(headers)
        response = client.post(
            '/api/v1/content/preview',
            headers=headers,
            json={'webapp_id': webapp_id, 'platform': 'tiktok', 'format': 'short_video_brief', 'offer': 'Book a trail ride'},
        )
        self.assertEqual(response.status_code, 200, response.text)
        preview = response.json()['preview']
        structured = preview['structured_output']
        self.assertEqual(preview['intent'], 'short_video')
        self.assertIn('scene_by_scene_script', structured)
        self.assertIn(preview['media']['media_state'], {'script_only', 'not_rendered', 'unavailable'})
        self.assertNotIn('picsum', str(preview).lower())
        self.assertNotIn('placeholder', str(preview).lower())

    def test_avatar_and_voiceover_are_script_only_without_fake_urls(self):
        headers = self.register_and_login('avatar@example.com')
        webapp_id = self.create_business(headers)
        avatar = client.post(
            '/api/v1/content/preview',
            headers=headers,
            json={'webapp_id': webapp_id, 'platform': 'instagram', 'format': 'talking_avatar_script'},
        )
        voice = client.post(
            '/api/v1/content/preview',
            headers=headers,
            json={'webapp_id': webapp_id, 'platform': 'instagram', 'format': 'voiceover_script'},
        )
        self.assertEqual(avatar.status_code, 200, avatar.text)
        self.assertEqual(voice.status_code, 200, voice.text)
        for payload in (avatar.json()['preview'], voice.json()['preview']):
            self.assertIn(payload['media']['media_state'], {'script_only', 'not_rendered', 'unavailable'})
            self.assertEqual(payload['media']['media_urls'], [])
            self.assertNotIn('example.com/media', str(payload).lower())

    def test_hashtags_do_not_leak_amarktai_for_non_amarktai_businesses(self):
        headers = self.register_and_login('hashtags@example.com')
        webapp_id = self.create_business(headers)
        response = client.post(
            '/api/v1/content/preview',
            headers=headers,
            json={'webapp_id': webapp_id, 'platform': 'instagram', 'format': 'text_post', 'offer': 'AIContent Automation'},
        )
        self.assertEqual(response.status_code, 200, response.text)
        hashtags = response.json()['preview']['hashtags']
        banned = {'#Amarktai', '#AmarktaiMarketing', '#AmarktaiAI', '#AIContent', '#MarketingAutomation'}
        self.assertTrue(set(hashtags).isdisjoint(banned))

    def test_regenerate_changes_angle_or_flags_duplicate(self):
        headers = self.register_and_login('regen@example.com')
        webapp_id = self.create_business(headers)
        preview = client.post(
            '/api/v1/content/preview',
            headers=headers,
            json={'webapp_id': webapp_id, 'platform': 'instagram', 'format': 'text_post'},
        ).json()
        saved = client.post('/api/v1/content/preview/save', headers=headers, json={'preview_id': preview['preview_id']})
        self.assertEqual(saved.status_code, 200, saved.text)
        content_id = saved.json()['id']
        original_rows = self.list_content(headers, webapp_id)
        original = next(item for item in original_rows if item['id'] == content_id)
        regenerated = client.post(
            f'/api/v1/content/items/{content_id}/regenerate',
            headers=headers,
            json={'feedback': 'different angle and CTA', 'variation_seed': 'seed-2'},
        )
        self.assertEqual(regenerated.status_code, 200, regenerated.text)
        rows = self.list_content(headers, webapp_id)
        latest = rows[0]
        self.assertTrue(latest['id'] != original['id'])
        self.assertTrue(latest['parent_content_id'] == content_id)
        self.assertTrue(latest['uniqueness_score'] != original['uniqueness_score'] or latest['warnings'])

    def test_providers_debug_and_asset_search_routes_return_real_structures(self):
        headers = self.register_and_login('providers@example.com')
        webapp_id = self.create_business(headers)
        debug = client.get('/api/v1/settings/providers/debug', headers=headers)
        self.assertEqual(debug.status_code, 200, debug.text)
        with patch('app.services.pixabay_client.PixabayClient.search_images', new=AsyncMock(return_value={'items': [{
            'id': 1,
            'tags': 'horse riding',
            'pageURL': 'https://pixabay.com/photos/horse-riding-1/',
            'previewURL': 'https://cdn.pixabay.com/photo-preview.jpg',
            'largeImageURL': 'https://cdn.pixabay.com/photo-large.jpg',
            'user': 'pixabay-user',
        }]})):
            assets = client.get(f'/api/v1/media/pixabay/search?business_id={webapp_id}&platform=instagram&media_type=image', headers=headers)
        self.assertEqual(assets.status_code, 200, assets.text)
        payload = assets.json()
        self.assertGreaterEqual(payload['count'], 1)
        item = payload['items'][0]
        self.assertEqual(item['provider'], 'pixabay')
        self.assertTrue(item['source_url'])


if __name__ == '__main__':
    unittest.main()
