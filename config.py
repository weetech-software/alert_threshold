class Config:
    def __init__(self, description, enable, script, metrics, exclude_hosts, value, operator, threshold_operator, alert_value, alert_methods):
        self.description = description
        self.enable = enable
        self.script = script
        self.metrics = metrics
        self.exclude_hosts = exclude_hosts
        self.value = value
        self.operator = operator
        self.threshold_operator = threshold_operator
        self.alert_value = alert_value
        self.alert_methods = alert_methods

    def __str__(self):
        return "description: %s, enable: %s, script : %s, metrics: [%s], exclude_hosts: [%s], value: %s, operator: %s, threshold_operator: %s, alert_value: %s" % (self.description, self.enable, self.script, ",".join(self.metrics), ",".join(self.exclude_hosts), self.value, self.operator, self.threshold_operator, self.alert_value)

    def __repr__(self):
        return self.__str__()

