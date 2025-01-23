# Ratio1 Edge Node (Naeural Edge Protocol Edge Node)

Welcome to the **Ratio1 Edge Node** repository, formerly known as the **Naeural Edge Protocol Edge Node**. As a pivotal component of the Ratio1 ecosystem, this Edge Node software empowers a decentralized, privacy-preserving, and secure edge computing network. By enabling a collaborative network of edge nodes, Ratio1 facilitates the secure sharing of resources and the seamless execution of computation tasks across diverse devices.

## Introduction

The Ratio1 Edge Node is a robust software solution designed to operate on edge devices, providing the essential functionality required to join and thrive within the Ratio1 network. Each Edge Node manages the device’s resources, executes computation tasks efficiently, and communicates securely with other nodes in the network. Leveraging the powerful Naeural Edge Protocol libraries—`naeural_core` and `naeural_client`—the Ratio1 Edge Node offers out-of-the-box usability starting in 2025. Users can deploy the Edge Node and SDK (`naeural_client`) effortlessly without the need for intricate configurations, local subscriptions, tenants, user accounts, passwords, or broker setups.

## Running the Edge Node

Deploying a Ratio1 Edge Node within a development network is straightforward. Execute the following Docker command to launch the node:

```bash
docker run -d --rm --name r1node --pull=always naeural/edge_node:develop
```

This command initializes the Ratio1 Edge Node in development mode, automatically connecting it to the Ratio1 development network and preparing it to receive computation tasks.

- `-d`: Runs the container in the background.
- `--rm`: Removes the container upon stopping.
- `--name r1node`: Assigns the name `r1node` to the container.
- `--pull=always`: Ensures the latest image version is always pulled.
- `naeural/edge_node:develop`: Specifies the Docker image to run.

### Preserving Node Data

To maintain node data across restarts, mount a persistent volume to the container using the following command:

```bash
docker run -d --rm --name r1node --pull=always -v r1vol:/edge_node/_local_cache/ naeural/edge_node:develop
```

- `-v r1vol:/edge_node/_local_cache/`: Mounts the `r1vol` volume to the `/edge_node/_local_cache/` directory within the container.

This setup ensures that all node data is stored in `r1vol`, preserving it between container restarts.

## Inspecting the Edge Node

After launching the Ratio1 Edge Node, you can inspect its status and view its self-generated identity by executing:

```bash
docker exec r1node get_node_info
```

This command retrieves comprehensive information about the node, including its current status and unique identity within the network such as below
```json
{
  "address": "0xai_A2pPf0lxZSZkGONzLOmhzndncc1VvDBHfF-YLWlsrG9m",
  "alias": "5ac5438a2775",
  "eth_address": "0xc440cdD0BBdDb5a271de07d3378E31Cb8D9727A5",
  "version_long": "v2.5.36 | core v7.4.23 | SDK 2.6.15",
  "version_short": "v2.5.36",
  "info": {
    "whitelist": []
  }
}
```

## Adding an Allowed Address

To authorize a specific address—such as an SDK address—to send computation tasks to your node, add it to the node’s whitelist with the following command:

```bash
docker exec r1node add_allowed <address> [<alias>]
```

- `<address>`: The address of the SDK permitted to send computation tasks to the node.
- `<alias>`: (Optional) A friendly alias for the address.

Upon execution, the node’s status will update, indicating that it is now ready to accept computation tasks from the specified SDK or Edge Node address.

Running the command with valid node address and alias:

```bash
docker exec r1node add_allowed 0xai_AthDPWc_k3BKJLLYTQMw--Rjhe3B6_7w76jlRpT6nDeX some-node-alias
```
will result in a result such as:

```json
{
  "address": "0xai_A2pPf0lxZSZkGONzLOmhzndncc1VvDBHfF-YLWlsrG9m",
  "alias": "5ac5438a2775",
  "eth_address": "0xc440cdD0BBdDb5a271de07d3378E31Cb8D9727A5",
  "version_long": "v2.5.36 | core v7.4.23 | SDK 2.6.15",
  "version_short": "v2.5.36",
  "info": {
    "whitelist": [
      "0xai_AthDPWc_k3BKJLLYTQMw--Rjhe3B6_7w76jlRpT6nDeX"
    ]
  }
}
```


## Stopping the Edge Node

To gracefully stop and remove the Ratio1 Edge Node container, use:

```bash
docker stop r1node
```

This command halts the container and ensures it is removed from the system.

## License

This project is licensed under the **Apache 2.0 License**. For detailed information, please refer to the [LICENSE](LICENSE) file.

## Contact

For further information, visit our website at [https://ratio1.ai](https://ratio1.ai) or reach out to us via email at [support@ratio1.ai](mailto:support@ratio1.ai).

## Project Financing Disclaimer

This project incorporates open-source components developed with the support of financing grants **SMIS 143488** and **SMIS 156084**, provided by the Romanian Competitiveness Operational Programme. We extend our gratitude for this support, which has been instrumental in advancing our work and enabling us to share these resources with the community.

The content and information within this repository reflect the authors' views and do not necessarily represent those of the funding agencies. The grants have specifically supported certain aspects of this open-source project, facilitating broader dissemination and collaborative development.

For inquiries regarding the funding and its impact on this project, please contact the authors directly.

## Citation

If you use the Ratio1 Edge Node in your research or projects, please cite it as follows:

```bibtex
@misc{Ratio1EdgeNode,
  author = {Ratio1.AI},
  title = {Ratio1: Edge Node},
  year = {2024-2025},
  howpublished = {\url{https://github.com/NaeuralEdgeProtocol/edge_node}},
}
```
