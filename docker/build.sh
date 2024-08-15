DEFAULT_TAG="dev"
export TAG="${1:-$DEFAULT_TAG}"
docker buildx build --file Dockerfile.${TAG} --secret id=HF_TOKEN,env=HF_TOKEN --progress=plain --platform linux/amd64 --load --tag amniotic:${TAG} --build-context amniotic=../ --build-context tools=../../fmtr.tools .