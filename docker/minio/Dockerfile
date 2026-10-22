# Build MinIO and the MinIO Client from their published Go modules. The upstream
# community images are no longer pullable from Docker Hub in this environment.
FROM golang:1.24-alpine AS build
RUN CGO_ENABLED=0 go install github.com/minio/minio@RELEASE.2025-10-15T17-29-55Z \
    && CGO_ENABLED=0 go install github.com/minio/mc@RELEASE.2025-08-13T08-35-41Z

FROM alpine:3.22
RUN apk add --no-cache su-exec \
    && adduser -D -u 10001 minio \
    && mkdir -p /data /home/minio \
    && chown -R minio:minio /data /home/minio
COPY --from=build /go/bin/minio /usr/local/bin/minio
COPY --from=build /go/bin/mc /usr/local/bin/mc
COPY --chmod=755 docker/minio/entrypoint.sh /usr/local/bin/loan-minio-entrypoint
ENTRYPOINT ["/usr/local/bin/loan-minio-entrypoint"]
