export class Band {
    top;
    bottom;
    clusterInfos = [];

    addClusterInfo(clusterInfo) {
        this.clusterInfos.push(clusterInfo);
        this.top ??= clusterInfo.rect.top;
        this.top = Math.min(this.top, clusterInfo.rect.top);
        this.bottom ??= clusterInfo.rect.bottom;
        this.bottom = Math.max(this.bottom, clusterInfo.rect.bottom);
    }

    merge(band) {
        for (const clusterInfo of band.clusterInfos) {
            this.addClusterInfo(clusterInfo);
        }
    }
}
