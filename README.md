# NFT parser

This repo reads an NFT from a chain and stores it to cloud SQL. The every first day of the month, the program emails the monthly report to a Email address.

## Disability

The project is containerized and is suppose be be executed on Google Kubernetes Engine. However, The network is not set up properly yet. The Docker image can still be executed locally with proper permission setup.

## Files

* `abi/`: directory that contains our target OpenSea NFT smart contract abi.
* `blockNumber.txt`: stores the next starting block in `eventParser` iteration (updated per iteration).
* `config.json`: defined monthly report sender and receivers.
* `eventParser.py`: main program logics.
* `requirements.txt`: packages used by `eventParser`
* `Dockerfile`: containerize the `eventParser.py`
* `kustomize/`: Directory of yaml manifest for GKE deployment.

## Configurations

Aside from `abi/`, `blockNumber.txt`(better to initialize as the deployed blockNumber of the target smart contract), and `config.json` (sender is string, while receiver is a list) mentioned above. Check the following as well:

* `./kustomize/base/4-nftparser-configmap.yaml`: `data.PERIOD_IN_HOUR` defines the sleep time between eventParser iterations in hour.
* `./kustomize/environments/lab2/deploy-with-secret-patch.yaml`: `/spec/template/spec/containers/0/image` defines image used.

## To start:

* Get permission to run gcloud and kubectl cmd.
* Switch to corresponding `cluster` and `namespace`

If there's a need to update the program:
```
docker build -f Dockerflie -t nftparser:[TAG_NAME]
docker tag nftparser:[TAG_NAME] gcr.io/metaduet/nftparser:[TAG_NAME]
docker push gcr.io/metaduet/nftparser:[TAG_NAME]
# modify `./kustomize/environments/lab2/deploy-with-secret-patch.yaml`
cd kustomize
kubectl apply -k environments/lab2
```

If a new cluster would be used: This allow GCP service-account to be used by Kubernetes service account. (https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)
```
annotate serviceaccount nftparser-ksa \
    --namespace default \
    iam.gke.io/gcp-service-account=nftparser-gsa@metaduet.iam.gserviceaccount.com
```
To run image locally:

* Make sure connection from local IP to Cloud sql DB is enabled.

