# scripts/send_to_requestbin.py


def run_action(artifact, config):
    """
    Sends a POST request to a specified URL with the provided data.

    Args:
        artifact: The data to be sent in the request
        config: Action-specific config object containing:
            - url: The target URL (required)
            - headers: Optional custom headers (optional)
            - data_key: Key for the payload data (defaults to "content")
    """
    import requests

    # Validate required config
    if "url" not in config:
        raise ValueError("URL not found in action config")

    # Get optional parameters
    headers = config.get("headers", {})
    data_key = config.get("data_key", "content")

    # Prepare payload
    payload = {data_key: artifact}

    # Send POST request to the specified URL
    response = requests.post(config["url"], json=payload, headers=headers)

    # Check if request was successful
    if response.status_code == 200:
        print(f"Successfully sent POST request to: {config['url']}")
        return response
    else:
        error_msg = f"Failed to send request. Status code: {response.status_code}"
        print(error_msg)
        raise requests.RequestException(error_msg)
