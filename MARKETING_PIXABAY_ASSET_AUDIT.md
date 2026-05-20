# Marketing Pixabay Asset Audit

## Added services
- `backend/app/services/pixabay_client.py`
- `backend/app/services/asset_query_builder.py`
- `backend/app/services/asset_relevance.py`
- `backend/app/services/pixabay_asset_router.py`

## Added endpoints
- `GET /api/v1/settings/pixabay/status`
- `POST /api/v1/settings/pixabay/test`
- `GET /api/v1/media/pixabay/search`
- `GET /api/v1/media/pixabay/photos`
- `GET /api/v1/media/pixabay/illustrations`
- `GET /api/v1/media/pixabay/vectors`
- `GET /api/v1/media/pixabay/videos`
- Unsupported truth endpoints:
  - `/media/pixabay/music`
  - `/media/pixabay/sound-effects`
  - `/media/pixabay/gifs`
  - `/media/pixabay/3d-models`
  - `/media/pixabay/users`

## Unsupported response contract
Returns:
```json
{
  "status": "not_supported_by_api",
  "message": "This Pixabay category is not available through the configured official API endpoint."
}
```

## Asset persistence endpoints
- `POST /api/v1/media/assets`
- `DELETE /api/v1/media/assets/{id}?confirm=true`
- `POST /api/v1/media/content/items/{id}/attach-asset`
- `DELETE /api/v1/media/content/items/{id}/assets/{asset_id}`
