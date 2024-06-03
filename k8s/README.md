# Naeural Edgenode k8s deployment

## TL;DR steps to deploy the neural edgenode on k8s

1. Edit `edgenode-config.yaml`
2. Run `kubectl apply -f edgenode-config.yaml`
3. Edit `edgenode-secrets.yaml`
4. Run `kubectl apply -f edgenode-secrets.yaml`
5. Run the service account setup with `kubectl apply -f edgenode-sa.yaml`
6. Setup storage with `kubectl apply -f edgenode-storage.yaml`
7. Finally fireup the edgenode with `kubectl apply -f edgenode-deployment.yaml`