# Builds the wallet chaincode ONCE into an image; each institution runs one container of it (chaincode as a service).
# Base images pinned by digest (2026-10-20); wallet binary sha256 9864dce34e3a483c2ce4a37b4261f0ebfd6ba815f5cc4e6844c64ef112455f26 (Go 1.25.14).
# go.mod and go.sum are FROZEN: every rebuild uses exactly the same library versions (reproducibility).
FROM golang:1.25-alpine@sha256:1ae0735f00daffa3aaf1363a5184c0d2dc55c78e3db4ec70241cdac97bf84b59 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 go build -mod=readonly -o /wallet .

FROM alpine:3.20@sha256:d9e853e87e55526f6b2917df91a2115c36dd7c696a35be12163d44e6e2a4b6bc
COPY --from=build /wallet /usr/local/bin/wallet
EXPOSE 9999
CMD ["wallet"]
