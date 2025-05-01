import rclpy
from rclpy.node import Node
from std_msgs.msg import String
import pymongo
import json

class DataListener(Node):
    def __init__(self):
        super().__init__('data_listener')
        self.coordinate_subscription_ = self.create_subscription(String, 'coordinates', self.coordinate_callback, 10)
        self.location_subscription_ = self.create_subscription(String, 'location', self.location_callback, 10) # Add location subscription here
        self.message_subscription_ = self.create_subscription(String, 'notifications', self.message_callback, 10)

        try:
            # MongoDB connection
            self.client = pymongo.MongoClient("mongodb+srv://amybishara847:angela15@cluster0.g4nzj.mongodb.net/goDrivesDB?retryWrites=true&w=majority")
            self.db = self.client["goDrivesDB"]
            self.car_collection = self.db["cars"]
            self.username = "car1"
            self.get_logger().info("Connected to MongoDB successfully.")
        except pymongo.errors.ConnectionFailure as e:
            self.get_logger().error(f"Failed to connect to MongoDB: {e}")
            self.client = None

    def coordinate_callback(self, msg):
        self.get_logger().info(f'Received Coordinates: {msg.data}')
        if self.client:
            try:
                coordinate_data = json.loads(msg.data)
                formatted_coordinates = {}
                for obj_type, coords in coordinate_data.items():
                    formatted_coordinates[obj_type] = {
                        "x": str(coords["x"]),
                        "y": str(coords["y"]),
                        "timestamp": str(self.get_clock().now().to_msg().sec)
                    }
                car_document = self.car_collection.find_one({"username": self.username})
                if car_document:
                    self.get_logger().info(f"Car document with username '{self.username}' found.")
                    result = self.car_collection.update_one(
                        {"username": self.username},
                        {"$set": {"coordinates": formatted_coordinates}}
                    )
                    if result.modified_count > 0:
                        self.get_logger().info("Coordinate data replaced in MongoDB.")
                    else:
                        self.get_logger().warn("No modifications were made to the Car document.")
                else:
                    self.get_logger().warn(f"Car document with username '{self.username}' not found.")
            except Exception as e:
                self.get_logger().error(f"Failed to save coordinate data to MongoDB: {e}")
        else:
            self.get_logger().warn("MongoClient is None, cannot save to DB")

    def location_callback(self, msg):
        try:
            location_data = json.loads(msg.data)
            self.get_logger().info(f'Received Location: {location_data}')
        except json.JSONDecodeError as e:
            self.get_logger().error(f"Failed to decode location data: {e}, Data: {msg.data}")

    def message_callback(self, msg):
        self.get_logger().info(f'Received Notification: {msg.data}')
        if self.client:
            try:
                car_document = self.car_collection.find_one({"username": self.username})
                if car_document:
                    self.get_logger().info(f"Car document with username '{self.username}' found.")
                    notification_data = [{
                        "message": msg.data,
                        "timestamp": str(self.get_clock().now().to_msg().sec)
                    }]
                    result = self.car_collection.update_one(
                        {"username": self.username},
                        {"$set": {"notifications": notification_data}}
                    )
                    if result.modified_count > 0:
                        self.get_logger().info("Notification data replaced in MongoDB.")
                    else:
                        self.get_logger().warn("No modifications were made to the Car document.")
                else:
                    self.get_logger().warn(f"Car document with username '{self.username}' not found.")
            except Exception as e:
                self.get_logger().error(f"Failed to save notification data to MongoDB: {e}")
        else:
            self.get_logger().warn("MongoClient is None, cannot save to DB")

def main(args=None):
    rclpy.init(args=args)
    data_listener = DataListener()
    rclpy.spin(data_listener)
    data_listener.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()