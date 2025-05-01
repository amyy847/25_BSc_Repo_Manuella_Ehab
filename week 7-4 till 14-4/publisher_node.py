import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import random
import time
import json
import pymongo

class DataPublisher(Node):
    def __init__(self):
        super().__init__('data_publisher')
        self.coordinate_publisher_ = self.create_publisher(String, 'coordinates', 10)
        self.location_publisher_ = self.create_publisher(String, 'location', 10) #location publisher
        self.message_publisher_ = self.create_publisher(String, 'notifications', 10)
        self.coordinate_timer_ = self.create_timer(3.0, self.publish_coordinates)
        self.location_timer_ = self.create_timer(5.0, self.publish_location) #location timer
        self.notification_timer_ = self.create_timer(20.0, self.publish_notification)

        # Define screen dimensions (typical mobile screen dimensions)
        self.screen_width = 800
        self.screen_height = 1280
        self.padding = 50

        try:
            # MongoDB connection
            self.client = pymongo.MongoClient("mongodb+srv://amybishara847:angela15@cluster0.g4nzj.mongodb.net/goDrivesDB?retryWrites=true&w=majority")
            self.db = self.client["goDrivesDB"]
            self.car_collection = self.db["cars"]
            self.get_logger().info("Connected to MongoDB successfully.")
        except pymongo.errors.ConnectionFailure as e:
            self.get_logger().error(f"Failed to connect to MongoDB: {e}")
            self.client = None

    def publish_coordinates(self):
        regions = self.get_screen_regions()
        region = random.choice(list(regions.keys()))

        coordinate_data = {
            "pedestrian": self.generate_coordinates_in_region(regions["top_left" if region == "bottom_right" else "bottom_right"]),
            "vehicle": self.generate_coordinates_in_region(regions["top_right" if region == "bottom_left" else "bottom_left"]),
            "scene": self.generate_coordinates_in_region(regions[region]),
        }

        coordinate_msg = String()
        coordinate_msg.data = json.dumps(coordinate_data)

        self.get_logger().info(f'Publishing Coordinates: {coordinate_msg.data}')
        self.coordinate_publisher_.publish(coordinate_msg)

    def publish_location(self):
        if self.client:
            try:
                cars = self.car_collection.find({})
                for car in cars:
                    # Check if all required fields are present
                    if "username" in car and "currentLocation" in car:
                        username = car["username"]
                        current_location = car["currentLocation"]

                        # Validate individual fields
                        latitude = current_location.get("latitude")
                        longitude = current_location.get("longitude")
                        altitude = current_location.get("altitude")
                        speed = car.get("currentSpeed")

                        if latitude is not None and longitude is not None and altitude is not None and speed is not None:
                            location_data = {
                                "username": username,
                                "speed": str(speed),
                                "latitude": str(latitude),
                                "longitude": str(longitude),
                                "altitude": str(altitude),
                                "timestamp": str(self.get_clock().now().to_msg().sec)
                            }

                            location_msg = String()
                            location_msg.data = json.dumps(location_data)

                            self.get_logger().info(f'Publishing Location: {location_msg.data}')
                            self.location_publisher_.publish(location_msg)
                        else:
                            self.get_logger().warn(f"Skipping car '{username}' due to missing data: "
                                                   f"latitude={latitude}, longitude={longitude}, altitude={altitude}, speed={speed}")
                    else:
                        self.get_logger().warn(f"Skipping car due to missing 'username' or 'currentLocation': {car}")
            except Exception as e:
                self.get_logger().error(f"Failed to fetch location data from MongoDB: {e}")
        else:
            self.get_logger().warn("MongoClient is None, cannot fetch location data from DB")

    def get_screen_regions(self):
        mid_x = self.screen_width / 2
        mid_y = self.screen_height / 2

        return {
            "top_left": {"x_min": self.padding, "x_max": mid_x - self.padding, "y_min": self.padding, "y_max": mid_y - self.padding},
            "top_right": {"x_min": mid_x + self.padding, "x_max": self.screen_width - self.padding, "y_min": self.padding, "y_max": mid_y - self.padding},
            "bottom_left": {"x_min": self.padding, "x_max": mid_x - self.padding, "y_min": mid_y + self.padding, "y_max": self.screen_height - self.padding},
            "bottom_right": {"x_min": mid_x + self.padding, "x_max": self.screen_width - self.padding, "y_min": mid_y + self.padding, "y_max": self.screen_height - self.padding},
            "center": {"x_min": mid_x - 50, "x_max": mid_x + 50, "y_min": mid_y - 50, "y_max": mid_y + 50}
        }

    def generate_coordinates_in_region(self, region):
        return {
            "x": str(random.uniform(region["x_min"], region["x_max"])),
            "y": str(random.uniform(region["y_min"], region["y_max"])),
            "z": str(random.uniform(-5, 5)),
            "timestamp": str(self.get_clock().now().to_msg().sec)
        }

    def publish_notification(self):
        message_msg = String()
        message_msg.data = f"Random notification at time: {self.get_clock().now().to_msg().sec}"

        self.get_logger().info(f'Publishing Notification: {message_msg.data}')
        self.message_publisher_.publish(message_msg)

def main(args=None):
    rclpy.init(args=args)
    data_publisher = DataPublisher()
    rclpy.spin(data_publisher)
    data_publisher.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()