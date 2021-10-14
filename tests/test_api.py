

def test_ui(fujiclient):
    response = fujiclient.get('/fuji/api/v1/ui/')
    print(response.data)
    assert response.status_code == 200
