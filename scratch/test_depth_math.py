import numpy as np
import cv2

def test_depth_estimation():
    # Tag size in cm
    s = 7.0
    # Object corners in tag plane (Z=0)
    obj_points = np.array([
        [0, 0, 0],
        [s, 0, 0],
        [s, s, 0],
        [0, s, 0]
    ], dtype=np.float32)

    # Assume a camera at distance D=50cm, focal length f=1000, looking straight down
    # (Actually at an angle to make it interesting)
    # Pose: R = Eye, t = [0, 0, 50]
    K = np.array([
        [1000, 0, 500],
        [0, 1000, 400],
        [0, 0, 1]
    ], dtype=np.float32)

    dist_coeffs = np.zeros(4)
    
    # 45 degree tilt around X
    theta = np.radians(30)
    R = np.array([
        [1, 0, 0],
        [0, np.cos(theta), -np.sin(theta)],
        [0, np.sin(theta), np.cos(theta)]
    ], dtype=np.float32)
    t = np.array([0, 0, 50], dtype=np.float32).reshape(3, 1)

    # Project corners to image
    img_points, _ = cv2.projectPoints(obj_points, R, t, K, dist_coeffs)
    img_points = img_points.reshape(-1, 2)

    print("Projected Image Points:\n", img_points)

    # Now try to recover D and R, t using only img_points, obj_points, and guessed K
    success, rvec, tvec = cv2.solvePnP(obj_points, img_points, K, dist_coeffs)
    print("\nRecovered tvec:\n", tvec)
    print("Recovered distance D:", np.linalg.norm(tvec))

    # Now, try to project a point at height h=5cm above the tag
    h = 5.0
    obj_h = np.array([
        [0, 0, -h], # Note: Z points "into" the page if standard PnP? 
        # Actually, in OBJ points, the tag is at Z=0. 
        # If the camera is at tvec, and looking at the tag.
        # If the hand is on the table, it's above the tag.
        # But wait, where is the hand? In front of the tag?
        # If the tag is on the table (Z_tag=0) and camera is above (Z_cam > 0).
        # Hand is at Z_hand > 0.
        [s, 0, -h] 
    ], dtype=np.float32)
    # Wait, my obj_points were at Z=0. Let's say Z points UP from the table.
    # But solvePnP returns pose where Z points ALONG the camera axis.
    
    # Let's clarify the coordinate system.
    # Tag corners in its own frame: (0,0,0), (s,0,0), (s,s,0), (0,s,0)
    # If the hand is "on top" of the tag, its points are at (X, Y, h) 
    # OR (X, Y, -h) depending on the normal.
    # Let's say the normal points UP, so h is positive.
    
    # Let's re-run projectPoints for h=5
    obj_points_h = np.array([
        [0, 0, -5], # Assuming hand is 5cm ABOVE the tag
        [5, 0, -5]
    ], dtype=np.float32)
    img_points_h, _ = cv2.projectPoints(obj_points_h, R, t, K, dist_coeffs)
    img_points_h = img_points_h.reshape(-1, 2)
    print("\nImage points at height 5cm:\n", img_points_h)

    # Now, if we used the tag-plane homography to measure these:
    H, _ = cv2.findHomography(img_points, obj_points[:, :2])
    
    def pixel_to_cm(u, v, H):
        pt = np.array([u, v, 1], dtype=np.float32)
        mapped = H @ pt
        return mapped[:2] / mapped[2]

    cm_0 = pixel_to_cm(img_points_h[0,0], img_points_h[0,1], H)
    cm_1 = pixel_to_cm(img_points_h[1,0], img_points_h[1,1], H)
    measured_len = np.linalg.norm(cm_1 - cm_0)
    print("\nMeasured length on tag plane (wrong):", measured_len)
    print("True length:", 5.0)
    print("Ratio:", measured_len / 5.0)

    # Now correction using depth D
    D = np.linalg.norm(tvec)
    # Correction factor: 1 - h/D (simplified for straight down)
    corrected_len_simple = measured_len * (1 - h/D)
    print("Corrected length (simple):", corrected_len_simple)

    # Better correction: backproject ray and intersect plane Z=-h
    R_mat, _ = cv2.Rodrigues(rvec)
    # Ray in tag coords: X_t = R_mat^T * (K^-1 * [u,v,1] * lambda - tvec)
    def ray_intersect_plane(u, v, K, R_mat, tvec, h_target):
        # Camera center in tag coords
        C_tag = -R_mat.T @ tvec
        
        # Pixel ray in camera coords
        K_inv = np.linalg.inv(K)
        r_cam = K_inv @ np.array([u, v, 1], dtype=np.float32)
        
        # Ray direction in tag coords
        r_tag = R_mat.T @ r_cam
        
        # Point on ray: C_tag + alpha * r_tag
        # Condition: Point_z = h_target
        # C_tag_z + alpha * r_tag_z = h_target
        alpha = (h_target - C_tag[2]) / r_tag[2]
        
        P_tag = C_tag + alpha * r_tag
        return P_tag

    p_corrected_0 = ray_intersect_plane(img_points_h[0,0], img_points_h[0,1], K, R_mat, tvec, -h)
    p_corrected_1 = ray_intersect_plane(img_points_h[1,0], img_points_h[1,1], K, R_mat, tvec, -h)
    corrected_len_full = np.linalg.norm(p_corrected_1 - p_corrected_0)
    print("Corrected length (full projection):", corrected_len_full)

if __name__ == "__main__":
    test_depth_estimation()
