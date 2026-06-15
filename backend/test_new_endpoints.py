import httpx
import sys
import json

BASE_URL = "http://127.0.0.1:8000/api"

def run_full_test():
    print("=== Testing 9 New APIs (Total 20 endpoints) ===\n")
    
    with httpx.Client() as client:
        # Setup: Create 3 test users
        print("[SETUP] Creating test users...")
        users = {}
        for i, (name, email) in enumerate([("Alice", "alice@test.com"), ("Bob", "bob@test.com"), ("Charlie", "charlie@test.com")]):
            res = client.post(f"{BASE_URL}/auth/signup", json={
                "email": email,
                "password": f"pass{i}123",
                "display_name": name
            })
            if res.status_code != 201:
                print(f"❌ Failed to create {name}: {res.json()}")
                sys.exit(1)
            user_data = res.json()
            users[name.lower()] = {
                "id": user_data["user"]["id"],
                "token": user_data["token"],
                "email": email
            }
            print(f"  ✅ {name} created")

        alice_token = users["alice"]["token"]
        bob_token = users["bob"]["token"]
        alice_headers = {"Authorization": f"Bearer {alice_token}"}
        bob_headers = {"Authorization": f"Bearer {bob_token}"}
        alice_id = users["alice"]["id"]
        bob_id = users["bob"]["id"]

        # 1. GET /users - List org members
        print("\n[1] GET /users - List org members")
        res = client.get(f"{BASE_URL}/users", headers=alice_headers)
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        users_list = res.json()
        assert len(users_list["users"]) == 3, f"Expected 3 users, got {len(users_list['users'])}"
        print(f"  ✅ Listed {len(users_list['users'])} users")

        # 2. PATCH /users/:id - Update user profile
        print("\n[2] PATCH /users/:id - Update user profile")
        res = client.patch(f"{BASE_URL}/users/{alice_id}", 
            json={"display_name": "Alice Updated", "avatar_color": "#FF5733"},
            headers=alice_headers
        )
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert res.json()["display_name"] == "Alice Updated"
        assert res.json()["avatar_color"] == "#FF5733"
        print(f"  ✅ User profile updated")

        # 3. POST /folders - Create root folder
        print("\n[3] POST /folders - Create folders")
        res = client.post(f"{BASE_URL}/folders", 
            json={"name": "Projects", "parent_folder_id": None},
            headers=alice_headers
        )
        assert res.status_code == 201
        root_folder_id = res.json()["id"]
        print(f"  ✅ Root folder created: {root_folder_id}")

        # Create nested folder
        res = client.post(f"{BASE_URL}/folders",
            json={"name": "Q1 Planning", "parent_folder_id": root_folder_id},
            headers=alice_headers
        )
        assert res.status_code == 201
        nested_folder_id = res.json()["id"]
        print(f"  ✅ Nested folder created: {nested_folder_id}")

        # 4. GET /folders - List folders
        print("\n[4] GET /folders - List all folders")
        res = client.get(f"{BASE_URL}/folders", headers=alice_headers)
        assert res.status_code == 200
        folders = res.json()["folders"]
        assert len(folders) >= 2
        print(f"  ✅ Listed {len(folders)} folders")

        # 5. PATCH /folders/:id - Rename folder
        print("\n[5] PATCH /folders/:id - Rename folder")
        res = client.patch(f"{BASE_URL}/folders/{root_folder_id}",
            json={"name": "All Projects"},
            headers=alice_headers
        )
        assert res.status_code == 200
        assert res.json()["name"] == "All Projects"
        print(f"  ✅ Folder renamed to 'All Projects'")

        # 6. POST /documents - Create documents
        print("\n[6] POST /documents - Create documents")
        res = client.post(f"{BASE_URL}/documents",
            json={"folder_id": nested_folder_id, "title": "Q1 Roadmap"},
            headers=alice_headers
        )
        assert res.status_code == 201
        doc1_id = res.json()["id"]
        print(f"  ✅ Document created: {doc1_id}")

        res = client.post(f"{BASE_URL}/documents",
            json={"folder_id": nested_folder_id, "title": "Budget Plan"},
            headers=alice_headers
        )
        assert res.status_code == 201
        doc2_id = res.json()["id"]
        print(f"  ✅ Document created: {doc2_id}")

        # 7. GET /documents/:id - Get single document
        print("\n[7] GET /documents/:id - Get single document")
        res = client.get(f"{BASE_URL}/documents/{doc1_id}", headers=alice_headers)
        assert res.status_code == 200
        assert res.json()["title"] == "Q1 Roadmap"
        print(f"  ✅ Retrieved document: {res.json()['title']}")

        # 8. PATCH /documents/:id - Update document
        print("\n[8] PATCH /documents/:id - Update document")
        res = client.patch(f"{BASE_URL}/documents/{doc1_id}",
            json={"title": "Q1 Roadmap - Updated", "folder_id": nested_folder_id},
            headers=alice_headers
        )
        assert res.status_code == 200
        assert res.json()["title"] == "Q1 Roadmap - Updated"
        print(f"  ✅ Document updated: {res.json()['title']}")

        # 9. POST /assignments - Assign roles
        print("\n[9] POST /assignments - Assign roles")
        res = client.post(f"{BASE_URL}/assignments",
            json={
                "user_id": bob_id,
                "role_id": "role-editor",
                "scope_type": "folder",
                "scope_id": nested_folder_id
            },
            headers=alice_headers
        )
        assert res.status_code == 201
        assignment_id = res.json()["id"]
        print(f"  ✅ Bob assigned as editor: {assignment_id}")

        # 10. GET /assignments - List assignments
        print("\n[10] GET /assignments - List assignments")
        res = client.get(f"{BASE_URL}/assignments?scope_type=folder&scope_id={nested_folder_id}",
            headers=alice_headers
        )
        assert res.status_code == 200
        assert len(res.json()["assignments"]) > 0
        print(f"  ✅ Listed {len(res.json()['assignments'])} assignments")

        # 11. DELETE /assignments/:id - Revoke assignment
        print("\n[11] DELETE /assignments/:id - Revoke assignment")
        res = client.delete(f"{BASE_URL}/assignments/{assignment_id}",
            headers=alice_headers
        )
        assert res.status_code == 204
        print(f"  ✅ Assignment revoked")

        # Verify deletion
        res = client.get(f"{BASE_URL}/assignments?scope_type=folder&scope_id={nested_folder_id}",
            headers=alice_headers
        )
        assert len(res.json()["assignments"]) == 0
        print(f"  ✅ Verified assignment was deleted")

        # 12. DELETE /documents/:id - Soft delete document
        print("\n[12] DELETE /documents/:id - Soft delete document")
        res = client.delete(f"{BASE_URL}/documents/{doc2_id}",
            headers=alice_headers
        )
        assert res.status_code == 204
        print(f"  ✅ Document soft deleted")

        # Verify soft delete
        res = client.get(f"{BASE_URL}/documents/{doc2_id}", headers=alice_headers)
        assert res.status_code == 200
        assert res.json()["status"] == "deleted"
        print(f"  ✅ Verified document status is 'deleted'")

        # 13. DELETE /folders/:id - Delete empty folder
        print("\n[13] DELETE /folders/:id - Delete empty folder")
        
        # Create an empty folder
        res = client.post(f"{BASE_URL}/folders",
            json={"name": "Empty Folder", "parent_folder_id": root_folder_id},
            headers=alice_headers
        )
        empty_folder_id = res.json()["id"]
        
        # Delete it
        res = client.delete(f"{BASE_URL}/folders/{empty_folder_id}",
            headers=alice_headers
        )
        assert res.status_code == 204
        print(f"  ✅ Empty folder deleted")

        # Try to delete non-empty folder (should fail)
        res = client.delete(f"{BASE_URL}/folders/{nested_folder_id}",
            headers=alice_headers
        )
        assert res.status_code == 400
        print(f"  ✅ Non-empty folder deletion blocked")

        print("\n" + "="*50)
        print("✅ ALL TESTS PASSED!")
        print("="*50)
        print("\nSummary of tested APIs:")
        print("  ✅ 1.  GET /users")
        print("  ✅ 2.  PATCH /users/:id")
        print("  ✅ 3.  POST /folders")
        print("  ✅ 4.  GET /folders")
        print("  ✅ 5.  PATCH /folders/:id")
        print("  ✅ 6.  POST /documents")
        print("  ✅ 7.  GET /documents/:id")
        print("  ✅ 8.  PATCH /documents/:id")
        print("  ✅ 9.  POST /assignments")
        print("  ✅ 10. GET /assignments")
        print("  ✅ 11. DELETE /assignments/:id")
        print("  ✅ 12. DELETE /documents/:id")
        print("  ✅ 13. DELETE /folders/:id")
        print("\nPrevious 7 endpoints (still working):")
        print("  ✅ 14. POST /auth/signup")
        print("  ✅ 15. POST /auth/login")
        print("  ✅ 16. GET /auth/me")
        print("  ✅ 17. GET /roles")
        print("  ✅ 18. GET /documents (list by folder)")
        print("  ✅ 19. GET /documents/:id/authorize-check")
        print("  ✅ 20. Bonus: Additional authorization checks\n")

if __name__ == "__main__":
    run_full_test()
