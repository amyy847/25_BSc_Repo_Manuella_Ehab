import numpy as np
import cv2
import cv2.aruco as aruco
import glob
import os

# --- ChArUco Board Configuration ---
# VERIFY THESE VALUES BASED ON YOUR GENERATED calib.io PATTERN

# Number of squares on the board (inner corners will be (COLUMNS-1, ROWS-1))
COLUMNS_SQUARES = 11  # Number of columns of squares
ROWS_SQUARES = 8    # Number of rows of squares

# Physical size of the board elements (ensure units are consistent, e.g., meters)
SQUARE_LENGTH_M = 0.015  # Example: 15mm checker width converted to meters
MARKER_LENGTH_M = 0.011 # Example: Marker length is 75% of square length. Adjust if needed.
                               # This is the side length of the black ArUco marker.

# ArUco Dictionary
# IMPORTANT: Verify this matches the dictionary used to generate your ChArUco board in calib.io
# Common options: aruco.DICT_4X4_50, aruco.DICT_4X4_100, aruco.DICT_5X5_100, etc.
ARUCO_DICTIONARY_NAME = aruco.DICT_4X4_50 # ****** PLEASE VERIFY THIS ******
# --- End of Configuration ---

# Path to your calibration images
IMAGES_PATH = 'tablet_calibration/*.jpg'  # CHANGE THIS to your images path and extension-

# Initialize the ArUco dictionary
dictionary = aruco.getPredefinedDictionary(ARUCO_DICTIONARY_NAME)

# Create ChArUco board object
# Note: OpenCV's CharucoBoard uses (squaresX, squaresY) convention
board = aruco.CharucoBoard((COLUMNS_SQUARES, ROWS_SQUARES), SQUARE_LENGTH_M, MARKER_LENGTH_M, dictionary)

# Arrays to store object points and image points from all the images.
all_charuco_corners = [] # Stores 2D points in image plane from all images
all_charuco_ids = []     # Stores corresponding IDs for Charuco corners

# Prepare object points. These are the 3D coordinates of the Charuco corners.
# The CharucoBoard object (board.chessboardCorners) provides these canonical coordinates.

images = glob.glob(IMAGES_PATH)

if not images:
    print(f"No images found at path: {IMAGES_PATH}")
    print("Please check the path and make sure your images are there.")
else:
    print(f"Found {len(images)} images for calibration.")

    img_size = None # To store image dimensions for calibrateCamera

    for fname in images:
        img = cv2.imread(fname)
        if img is None:
            print(f"Failed to load image: {fname}")
            continue

        if img_size is None:
            img_size = img.shape[:2] # (height, width)

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect ArUco markers
        marker_corners, marker_ids, rejected_img_points = aruco.detectMarkers(
            gray,
            dictionary
        )

        # If markers are detected, interpolate ChArUco corners
        if marker_ids is not None and len(marker_ids) > 0:
            ret, charuco_corners, charuco_ids = aruco.interpolateCornersCharuco(
                markerCorners=marker_corners,
                markerIds=marker_ids,
                image=gray,
                board=board
            )

            # If enough ChArUco corners are found
            if charuco_corners is not None and charuco_ids is not None and len(charuco_corners) > 3:
                all_charuco_corners.append(charuco_corners)
                all_charuco_ids.append(charuco_ids)

                # Draw detected markers and ChArUco corners (optional visualization)
                aruco.drawDetectedMarkers(img, marker_corners, marker_ids)
                aruco.drawDetectedCornersCharuco(img, charuco_corners, charuco_ids, (0,255,0))
            else:
                print(f"Not enough ChArUco corners found in {fname}")
        else:
            print(f"No ArUco markers detected in {fname}")

        # Display the image (optional)
        cv2.imshow('img', img)
        cv2.waitKey(200) # Display for 0.2 seconds

    cv2.destroyAllWindows()

    if len(all_charuco_corners) > 0 and len(all_charuco_ids) > 0:
        print(f"\nSuccessfully processed {len(all_charuco_corners)} images with ChArUco corners.")

        # Calibrate the camera
        # ret: Root Mean Square (RMS) re-projection error.
        # mtx: Camera matrix (fx, fy, cx, cy)
        # dist: Distortion coefficients (k1, k2, p1, p2, k3)
        # rvecs: Rotation vectors for each view
        # tvecs: Translation vectors for each view
        try:
            ret, mtx, dist, rvecs, tvecs = aruco.calibrateCameraCharuco(
                charucoCorners=all_charuco_corners,
                charucoIds=all_charuco_ids,
                board=board,
                imageSize=img_size[::-1], # (width, height) expected by calibrateCameraCharuco
                cameraMatrix=None,       # Initial guess (optional)
                distCoeffs=None          # Initial guess (optional)
            )

            print("\nChArUco Camera Calibration Results:")
            print("----------------------------------")
            print(f"RMS re-projection error: {ret}")
            print("\nCamera Matrix (mtx):\n", mtx)
            print("\nDistortion Coefficients (dist):\n", dist)

            # Save calibration data
            calibration_data_file = 'zed_charuco_camera_calibration.npz'
            np.savez(calibration_data_file, mtx=mtx, dist=dist, rvecs=rvecs, tvecs=tvecs, rms=ret)
            print(f"\nCalibration data saved to {calibration_data_file}")

            # Example of undistorting an image (optional)
            if images:
                img_test = cv2.imread(images[0])
                h, w = img_test.shape[:2]
                newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w,h), 1, (w,h))

                dst = cv2.undistort(img_test, mtx, dist, None, newcameramtx)
                # x, y, w_roi, h_roi = roi # roi might not be perfectly tight with charuco
                # dst_cropped = dst[y:y+h_roi, x:x+w_roi]

                # cv2.imwrite('charuco_calibresult_original.png', img_test)
                # cv2.imwrite('charuco_calibresult_undistorted.png', dst)
                print("\nAn example undistorted image (charuco_calibresult_undistorted.png) can be saved if uncommented.")

        except cv2.error as e:
            print(f"Error during ChArUco calibration: {e}")
            print("This can happen if not enough corners were detected across images,")
            print("or if imageSize is incorrect, or if there's an issue with point correspondences.")
            print("Please check the number of detected corners and image paths.")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

    else:
        print("\nChArUco calibration failed. Not enough ChArUco corners found across all images.")