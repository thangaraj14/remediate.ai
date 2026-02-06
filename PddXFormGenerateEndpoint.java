package com.cloudhealth.svc.rightsizingframework.actuator;

import com.cloudhealth.svc.rightsizingframework.repository.PDDCostXformJobManager;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.actuate.endpoint.annotation.Endpoint;
import org.springframework.boot.actuate.endpoint.annotation.WriteOperation;
import org.springframework.stereotype.Component;

@Component
@Endpoint(id = "pddxformGenerateEndpoint")
@Slf4j
public class PddXFormGenerateEndpoint {

    @Autowired
    PDDCostXformJobManager jobManager;

    @WriteOperation
    public void generatePddXForm(Long customerId, Long accountId, String ownerId, boolean isUberPddEnabled) {
        try {
            jobManager.publishAWSPDDCostXformForCustomerAndAccount(customerId, accountId, ownerId, isUberPddEnabled);
        } catch (Exception e) {
            log.error("publishing PDDXform job failed for customer: {}, accountId: {}", customerId, accountId, e);
        }
    }
}
